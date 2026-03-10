# fs_database.py
#
# SQLite wrapper for the Agentic File Manager.
# Handles schema creation and upsert methods for volumes, directories, and files.

import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional

# ----------------------------------------------------------------------
# LLM-facing schema documentation
# ----------------------------------------------------------------------

LLM_DB_SCHEMA_DOC = """
You are interacting with a SQLite database that indexes files on disk.
It is designed for an agentic file manager. The database does NOT store
file contents, only metadata and basic media tags.

There are three main tables: `volumes`, `directories`, and `files`.

1) Table: volumes
-----------------
Each row represents a logical storage volume (e.g., a physical disk or
partition).

Columns:

- id               INTEGER PRIMARY KEY
    Surrogate key for internal use.

- volume_key       TEXT NOT NULL UNIQUE
    Stable identifier for the volume. On Windows this is typically
    derived from the volume serial number plus the filesystem name,
    e.g., "1234ABCD-NTFS". It should be treated as the primary logical
    identity of a volume across scans.

- root_path        TEXT
    Root path for this volume as seen by the OS, e.g. "C:\\" on Windows
    or "/" on POSIX. Primarily informational and may change if the drive
    is mounted differently.

- label            TEXT
    Human-readable volume label (if any), e.g. "Data" or "Backup".
    May be NULL.

- filesystem       TEXT
    Filesystem type string, e.g., "NTFS", "exFAT", etc. May be NULL.

- serial_number    TEXT
    Hex-encoded volume serial number string from the OS, e.g. "1234ABCD".
    May be NULL if the OS does not provide it.

2) Table: directories
---------------------
Each row represents a directory path on a given volume. Directories are
identified by (volume_id, dir_path).

Columns:

- id                       INTEGER PRIMARY KEY
    Surrogate key for internal use.

- volume_id                INTEGER NOT NULL
    Foreign key referencing volumes.id. Identifies which volume this
    directory lives on.

- dir_path                 TEXT NOT NULL
    Absolute directory path, with normalized separators (forward slashes
    used in this project), e.g. "C:/Users/Andre/Downloads". This path is
    unique per (volume_id, dir_path).

- dir_fingerprint          TEXT
    A fast, cheap fingerprint for the directory contents used to detect
    changes. It is usually a string of the form "count:max_mtime_ns",
    where:
        count        = number of direct children (files + subdirs)
        max_mtime_ns = max modification time of any direct child
    This is used as a heuristic: if the fingerprint changes, the
    directory likely needs to be rescanned.

- last_scan_started_ns     INTEGER
    Timestamp (in nanoseconds since the Unix epoch) when a scan of this
    directory last started. Used for bookkeeping or scheduling. May be
    NULL if never set.

- last_scan_completed_ns   INTEGER
    Timestamp (in nanoseconds since the Unix epoch) when a scan of this
    directory last fully completed. If this is NULL but
    last_scan_started_ns is not, the scan may have been interrupted.

3) Table: files
---------------
Each row represents a single file found under a directory on a volume.
Files are identified by (directory_id, name, extension).

The database DOES NOT store full paths directly; the full path can be
reconstructed as: <directories.dir_path> + "/" + <files.name> plus a dot
and extension if extension is not empty.

Columns:

- id                 INTEGER PRIMARY KEY
    Surrogate key for internal use.

- directory_id       INTEGER NOT NULL
    Foreign key referencing directories.id. Indicates which directory
    this file resides in.

- name               TEXT NOT NULL
    Stem of the file name without extension, as returned by the OS.
    Example: for "song.mp3", name = "song".

- extension          TEXT
    Lowercase file extension without the dot, e.g. "mp3" or "jpg".
    Empty or NULL if the file has no extension.

- size_bytes         INTEGER
    File size in bytes, as reported by the OS. May be NULL if unknown.

- mtime_ns           INTEGER
    Last modification time in nanoseconds since the Unix epoch. Derived
    from st_mtime_ns when available, or st_mtime * 1e9. Used for change
    detection and ordering by modification time.

- ctime_ns           INTEGER
    Creation time or "metadata change time" in nanoseconds since the Unix
    epoch, depending on the OS. May be NULL if unavailable.

- size_on_disk       INTEGER
    Estimated size on disk, in bytes, if the OS exposes compressed size
    (e.g., via GetCompressedFileSizeW on Windows). May be NULL if not
    available or not applicable.

- readonly           INTEGER NOT NULL DEFAULT 0
    Boolean flag (0 or 1). 1 means the OS marks this file as "read-only"
    at the filesystem level. This does NOT imply anything about access
    control lists; it only reflects the basic attribute bit.

- system             INTEGER NOT NULL DEFAULT 0
    Boolean flag (0 or 1). 1 means the OS marks this file as a "system"
    file. These are usually OS-managed and typically should not be
    manipulated or deleted by normal tools.

- is_symlink         INTEGER NOT NULL DEFAULT 0
    Boolean flag (0 or 1). 1 means this file entry is actually a symbolic
    link rather than a regular file. If an agent decides to manipulate
    files, it must be careful with symlinks to avoid unintended effects
    (e.g. deleting a symlink vs. the target).

- presence_state     INTEGER NOT NULL DEFAULT 0
    Integer field tracking the file's presence relative to the most recent
    scan of this directory. Values:

        0 = PRESENT
            The file was observed during the latest scan.

        1 = PENDING_SCAN
            The file existed in a previous scan, and a new scan has
            started for this directory. All files in this directory are
            first set to PENDING_SCAN before rescanning.

        2 = MISSING
            After a scan completes, any file that remained PENDING_SCAN
            (never seen during the new scan) is marked MISSING. This
            indicates a file that used to exist but no longer seems to be
            present on disk.

    Agents must treat presence_state = 2 as "historical only". If a
    command references such a file, the agent should re-check the file
    system before taking action.

Media and audio/video fields
----------------------------

The following columns are optional metadata fields, populated when the
file appears to be a supported media type and ffprobe is available.
They may all be NULL for non-media files or when ffprobe is not installed.

- duration           REAL
    Media duration in seconds (float). NULL if not available.

- bitrate            INTEGER
    Overall media bitrate in bits per second, if known. NULL if unknown.

- codec              TEXT
    Primary codec name, e.g. "h264", "aac", "flac". NULL if unknown.

- framerate          REAL
    Video frame rate in frames per second, if known. NULL for audio-only
    or non-video files.

- image_format       TEXT
    Format name reported by ffprobe, e.g. "mp3", "matroska", "mjpeg".
    This is a container/format label, not necessarily the codec name.

- resolution_width   INTEGER
- resolution_height  INTEGER
    Pixel width and height for video or image streams, if available.

- sample_rate        INTEGER
    Audio sample rate in Hz, e.g. 44100 or 48000. NULL if unknown.

- channels           INTEGER
    Number of audio channels, e.g. 1 (mono), 2 (stereo). NULL if unknown.

Tag / metadata fields
---------------------

These fields attempt to capture common media tags (ID3, Vorbis comments,
etc.) in a normalized way. They may be NULL if the media file has no
tags or if ffprobe did not report them.

- tag_title          TEXT
    Track or item title, e.g. "My Song".

- tag_artist         TEXT
    Primary artist for the track, e.g. "Some Band".

- tag_album          TEXT
    Album or collection title.

- tag_album_artist   TEXT
    Album-level artist credit (often used for "Various Artists" albums).

- tag_track          TEXT
    Track number or track index within an album. This may be a bare
    integer ("5") or a string like "5/12".

- tag_date           TEXT
    Date or year associated with the media, often in formats like
    "1999", "1999-05-12", etc.

General notes for agents
------------------------

- Do NOT assume every column is non-NULL. Many fields are best-effort.
- The database is a snapshot of a past scan. When manipulating files,
  the agent should be prepared for mismatches between the database and
  the live filesystem (e.g., files deleted or moved outside this tool).
- Full file paths are reconstructed as:
      <directories.dir_path> + "/" + <files.name> + "." + <files.extension>
  (skip the dot + extension if extension is empty or NULL).
- The `system` flag is a strong hint that the file should be left alone
  unless explicitly requested by the user.
- The `presence_state` field is important for distinguishing current
  files from historical entries.
"""


# A structured, programmatic view of the schema, if needed for tools
LLM_TABLE_METADATA: Dict[str, Dict[str, Dict[str, str]]] = {
    "volumes": {
        "id":               {"type": "INTEGER", "meaning": "Primary key for a volume row."},
        "volume_key":       {"type": "TEXT",    "meaning": "Logical identity of the volume (e.g. serial+fs)."},
        "root_path":        {"type": "TEXT",    "meaning": "Root mount path of the volume (e.g. 'C:\\\\')."},
        "label":            {"type": "TEXT",    "meaning": "Human-readable volume label, if any."},
        "filesystem":       {"type": "TEXT",    "meaning": "Filesystem type, e.g. NTFS, exFAT."},
        "serial_number":    {"type": "TEXT",    "meaning": "Hex-encoded volume serial number, if available."},
    },
    "directories": {
        "id":                     {"type": "INTEGER", "meaning": "Primary key for a directory row."},
        "volume_id":              {"type": "INTEGER", "meaning": "FK to volumes.id, which volume this directory is on."},
        "dir_path":               {"type": "TEXT",    "meaning": "Absolute directory path (normalized)."},
        "dir_fingerprint":        {"type": "TEXT",    "meaning": "Fast fingerprint for directory contents (count:max_mtime_ns)."},
        "last_scan_started_ns":   {"type": "INTEGER", "meaning": "Nanosecond timestamp when last scan started."},
        "last_scan_completed_ns": {"type": "INTEGER", "meaning": "Nanosecond timestamp when last scan fully completed."},
    },
    "files": {
        "id":               {"type": "INTEGER", "meaning": "Primary key for a file row."},
        "directory_id":     {"type": "INTEGER", "meaning": "FK to directories.id, parent directory of this file."},
        "name":             {"type": "TEXT",    "meaning": "File name without extension."},
        "extension":        {"type": "TEXT",    "meaning": "Lowercase extension without dot, or NULL if none."},
        "size_bytes":       {"type": "INTEGER", "meaning": "File size in bytes."},
        "mtime_ns":         {"type": "INTEGER", "meaning": "Last modification time in nanoseconds since epoch."},
        "ctime_ns":         {"type": "INTEGER", "meaning": "Creation/metadata change time in nanoseconds since epoch."},
        "size_on_disk":     {"type": "INTEGER", "meaning": "Size on disk in bytes, if known (compressed size)."},
        "readonly":         {"type": "INTEGER", "meaning": "0/1 flag: 1 if file has OS read-only attribute."},
        "system":           {"type": "INTEGER", "meaning": "0/1 flag: 1 if file has OS system attribute."},
        "is_symlink":       {"type": "INTEGER", "meaning": "0/1 flag: 1 if this entry is a symbolic link."},
        "presence_state":   {"type": "INTEGER", "meaning": "0=PRESENT, 1=PENDING_SCAN, 2=MISSING (historical)."},
        "duration":         {"type": "REAL",    "meaning": "Media duration in seconds, if available."},
        "bitrate":          {"type": "INTEGER", "meaning": "Media bitrate in bits per second, if available."},
        "codec":            {"type": "TEXT",    "meaning": "Primary codec name for audio/video, if available."},
        "framerate":        {"type": "REAL",    "meaning": "Video frame rate in FPS, if available."},
        "image_format":     {"type": "TEXT",    "meaning": "Container/format label from ffprobe, if available."},
        "resolution_width": {"type": "INTEGER", "meaning": "Video/image width in pixels, if available."},
        "resolution_height":{"type": "INTEGER", "meaning": "Video/image height in pixels, if available."},
        "sample_rate":      {"type": "INTEGER", "meaning": "Audio sample rate in Hz, if available."},
        "channels":         {"type": "INTEGER", "meaning": "Number of audio channels, if available."},
        "tag_title":        {"type": "TEXT",    "meaning": "Media tag: track title."},
        "tag_artist":       {"type": "TEXT",    "meaning": "Media tag: track artist."},
        "tag_album":        {"type": "TEXT",    "meaning": "Media tag: album name."},
        "tag_album_artist": {"type": "TEXT",    "meaning": "Media tag: album artist credit."},
        "tag_track":        {"type": "TEXT",    "meaning": "Media tag: track number or index."},
        "tag_date":         {"type": "TEXT",    "meaning": "Media tag: date or year string."},
    },
}


def get_llm_schema_doc() -> str:
    """
    Return a human-readable but LLM-friendly description of the database schema.
    This is intended to be included in system prompts or tool descriptions.
    """
    return LLM_DB_SCHEMA_DOC



class FSDatabase:
    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        cur = self.conn.cursor()

        # Volumes table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS volumes (
                id INTEGER PRIMARY KEY,
                volume_key TEXT NOT NULL UNIQUE,
                root_path TEXT,
                label TEXT,
                filesystem TEXT,
                serial_number TEXT
            );
            """
        )

        # Directories table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS directories (
                id INTEGER PRIMARY KEY,
                volume_id INTEGER NOT NULL,
                dir_path TEXT NOT NULL,
                dir_fingerprint TEXT,
                last_scan_started_ns INTEGER,
                last_scan_completed_ns INTEGER,
                FOREIGN KEY(volume_id) REFERENCES volumes(id),
                UNIQUE(volume_id, dir_path)
            );
            """
        )

        # Files table (no hidden, no archive)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                directory_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                extension TEXT,
                size_bytes INTEGER,
                mtime_ns INTEGER,
                ctime_ns INTEGER,
                size_on_disk INTEGER,

                readonly INTEGER NOT NULL DEFAULT 0,
                system   INTEGER NOT NULL DEFAULT 0,
                is_symlink INTEGER NOT NULL DEFAULT 0,

                -- 0 = PRESENT, 1 = PENDING_SCAN, 2 = MISSING
                presence_state INTEGER NOT NULL DEFAULT 0,

                -- Media / metadata fields
                duration REAL,
                bitrate INTEGER,
                codec TEXT,
                framerate REAL,
                image_format TEXT,
                resolution_width INTEGER,
                resolution_height INTEGER,
                sample_rate INTEGER,
                channels INTEGER,

                -- Tag fields
                tag_title TEXT,
                tag_artist TEXT,
                tag_album TEXT,
                tag_album_artist TEXT,
                tag_track TEXT,
                tag_date TEXT,

                FOREIGN KEY(directory_id) REFERENCES directories(id),
                UNIQUE(directory_id, name, extension)
            );
            """
        )

        self.conn.commit()

    # ------------------------------------------------------------------
    # Volume helpers
    # ------------------------------------------------------------------

    def upsert_volume(
        self,
        volume_key: str,
        root_path: Optional[str] = None,
        label: Optional[str] = None,
        filesystem: Optional[str] = None,
        serial_number: Optional[str] = None,
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO volumes (volume_key, root_path, label, filesystem, serial_number)
            VALUES (:volume_key, :root_path, :label, :filesystem, :serial_number)
            ON CONFLICT(volume_key) DO UPDATE SET
                root_path     = excluded.root_path,
                label         = excluded.label,
                filesystem    = excluded.filesystem,
                serial_number = excluded.serial_number;
            """,
            {
                "volume_key": volume_key,
                "root_path": root_path,
                "label": label,
                "filesystem": filesystem,
                "serial_number": serial_number,
            },
        )
        self.conn.commit()

        cur.execute("SELECT id FROM volumes WHERE volume_key = ?;", (volume_key,))
        row = cur.fetchone()
        return int(row["id"])

    # ------------------------------------------------------------------
    # Directory helpers
    # ------------------------------------------------------------------

    def upsert_directory(
        self,
        volume_id: int,
        dir_path: str,
        dir_fingerprint: Optional[str] = None,
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO directories (volume_id, dir_path, dir_fingerprint)
            VALUES (:volume_id, :dir_path, :dir_fingerprint)
            ON CONFLICT(volume_id, dir_path) DO UPDATE SET
                dir_fingerprint = excluded.dir_fingerprint;
            """,
            {
                "volume_id": volume_id,
                "dir_path": dir_path,
                "dir_fingerprint": dir_fingerprint,
            },
        )
        self.conn.commit()

        cur.execute(
            "SELECT id FROM directories WHERE volume_id = ? AND dir_path = ?;",
            (volume_id, dir_path),
        )
        row = cur.fetchone()
        return int(row["id"])

    def begin_directory_scan(self, directory_id: int, scan_started_ns: Optional[int] = None) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE files
            SET presence_state = 1
            WHERE directory_id = ?;
            """,
            (directory_id,),
        )
        if scan_started_ns is not None:
            cur.execute(
                """
                UPDATE directories
                SET last_scan_started_ns = ?
                WHERE id = ?;
                """,
                (scan_started_ns, directory_id),
            )
        self.conn.commit()

    def end_directory_scan(self, directory_id: int, completed: bool = True, scan_completed_ns: Optional[int] = None) -> None:
        cur = self.conn.cursor()
        if completed:
            cur.execute(
                """
                UPDATE files
                SET presence_state = 2
                WHERE directory_id = ?
                  AND presence_state = 1;
                """,
                (directory_id,),
            )
        if scan_completed_ns is not None:
            cur.execute(
                """
                UPDATE directories
                SET last_scan_completed_ns = ?
                WHERE id = ?;
                """,
                (scan_completed_ns, directory_id),
            )
        self.conn.commit()

    # ------------------------------------------------------------------
    # File helpers
    # ------------------------------------------------------------------

    def upsert_file_record(self, directory_id: int, record: Dict[str, Any]) -> int:
        """
        Insert or update a file row for the given directory.

        'record' is the dict returned by fs_reader.collect_full_record.
        """
        name = record["name"]
        extension = record.get("extension")

        params = {
            "directory_id": directory_id,
            "name": name,
            "extension": extension,

            "size_bytes": record.get("size_bytes"),
            "mtime_ns": record.get("mtime_ns"),
            "ctime_ns": record.get("ctime_ns"),
            "size_on_disk": record.get("size_on_disk"),

            "readonly": int(record.get("readonly", 0)),
            "system": int(record.get("system", 0)),
            "is_symlink": int(record.get("is_symlink", 0)),

            "presence_state": 0,

            "duration": record.get("duration"),
            "bitrate": record.get("bitrate"),
            "codec": record.get("codec"),
            "framerate": record.get("framerate"),
            "image_format": record.get("image_format"),
            "resolution_width": record.get("resolution_width"),
            "resolution_height": record.get("resolution_height"),
            "sample_rate": record.get("sample_rate"),
            "channels": record.get("channels"),

            "tag_title": record.get("tag_title"),
            "tag_artist": record.get("tag_artist"),
            "tag_album": record.get("tag_album"),
            "tag_album_artist": record.get("tag_album_artist"),
            "tag_track": record.get("tag_track"),
            "tag_date": record.get("tag_date"),
        }

        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO files (
                directory_id, name, extension,
                size_bytes, mtime_ns, ctime_ns, size_on_disk,
                readonly, system, is_symlink,
                presence_state,
                duration, bitrate, codec, framerate,
                image_format, resolution_width, resolution_height,
                sample_rate, channels,
                tag_title, tag_artist, tag_album, tag_album_artist,
                tag_track, tag_date
            )
            VALUES (
                :directory_id, :name, :extension,
                :size_bytes, :mtime_ns, :ctime_ns, :size_on_disk,
                :readonly, :system, :is_symlink,
                :presence_state,
                :duration, :bitrate, :codec, :framerate,
                :image_format, :resolution_width, :resolution_height,
                :sample_rate, :channels,
                :tag_title, :tag_artist, :tag_album, :tag_album_artist,
                :tag_track, :tag_date
            )
            ON CONFLICT(directory_id, name, extension) DO UPDATE SET
                size_bytes        = excluded.size_bytes,
                mtime_ns          = excluded.mtime_ns,
                ctime_ns          = excluded.ctime_ns,
                size_on_disk      = excluded.size_on_disk,
                readonly          = excluded.readonly,
                system            = excluded.system,
                is_symlink        = excluded.is_symlink,
                presence_state    = excluded.presence_state,
                duration          = excluded.duration,
                bitrate           = excluded.bitrate,
                codec             = excluded.codec,
                framerate         = excluded.framerate,
                image_format      = excluded.image_format,
                resolution_width  = excluded.resolution_width,
                resolution_height = excluded.resolution_height,
                sample_rate       = excluded.sample_rate,
                channels          = excluded.channels,
                tag_title         = excluded.tag_title,
                tag_artist        = excluded.tag_artist,
                tag_album         = excluded.tag_album,
                tag_album_artist  = excluded.tag_album_artist,
                tag_track         = excluded.tag_track,
                tag_date          = excluded.tag_date;
            """,
            params,
        )
        self.conn.commit()

        cur.execute(
            """
            SELECT id FROM files
            WHERE directory_id = ? AND name = ? AND extension IS ?
            """,
            (directory_id, name, extension),
        )
        row = cur.fetchone()
        return int(row["id"]) if row is not None else -1

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
