# mock_fs_reader.py
"""
MockFSReader — an FSReader adapter that reads from a MockFiles virtual filesystem.

This allows scan_path_into_db to scan a MockFiles instance exactly as it would
scan the real OS filesystem, using the same code path.
"""

from typing import Iterator, Tuple, Dict, Any
from ..fs_reader import FSReader
from .mock_files import MockFiles


class MockFSReader(FSReader):
    """
    FSReader implementation backed by a MockFiles virtual filesystem.

    Delegates directory/file iteration to the MockFiles SQLite database
    and uses the MockFiles clock for now().
    """

    def __init__(self, mock_files: MockFiles):
        self._mf = mock_files

    @classmethod
    def from_file(cls, db_path: str) -> "MockFSReader":
        """
        Open a MockFiles database and return a MockFSReader wrapping it.

        The mock clock is automatically set past the latest file timestamp
        so that scan timestamps are chronologically after all file timestamps.
        """
        mf = MockFiles(db_path)

        # Find the latest file timestamp in the database
        cur = mf.db.conn.cursor()
        cur.execute("SELECT MAX(mtime_ns) as max_mt FROM files")
        row = cur.fetchone()
        max_ts = row["max_mt"] if row and row["max_mt"] is not None else 0

        # Also check the current clock — keep whichever is later
        current = mf.get_time()
        if max_ts >= current:
            mf.set_time(max_ts)
            mf._advance_time()  # one tick past the latest file

        return cls(mf)

    # -----------------------------------------------------------------
    # FSReader interface
    # -----------------------------------------------------------------

    def now(self) -> int:
        """
        Return the mock clock time, then advance by one second.

        Each call returns a unique, monotonically increasing timestamp.
        """
        ts = self._mf.get_time()
        self._mf._advance_time()
        return ts

    def get_volume_info(self, root_path: str) -> Dict[str, Any]:
        abs_path = self._mf._normalize_path(root_path)
        volume_id = self._mf._get_volume_id_for_path(abs_path)
        if volume_id is None:
            raise ValueError(f"Volume not mounted: {abs_path}")

        cur = self._mf.db.conn.cursor()
        cur.execute("SELECT * FROM volumes WHERE id = ?", (volume_id,))
        row = cur.fetchone()
        return {
            "root_path": row["root_path"],
            "label": row["label"],
            "filesystem": row["filesystem"],
            "serial_number": row["serial_number"],
            "volume_key": row["volume_key"],
        }

    def iter_dirs(self, root_dir: str) -> Iterator[str]:
        abs_path = self._mf._normalize_path(root_dir)
        volume_id = self._mf._get_volume_id_for_path(abs_path)
        if volume_id is None:
            return

        dir_path_db = abs_path.replace("\\", "/")
        like_prefix = dir_path_db.rstrip("/")

        cur = self._mf.db.conn.cursor()
        cur.execute(
            """
            SELECT dir_path FROM directories
            WHERE volume_id = ?
              AND (dir_path = ? OR dir_path LIKE ?)
            ORDER BY dir_path
            """,
            (volume_id, dir_path_db, like_prefix + "/%"),
        )
        for row in cur.fetchall():
            yield row["dir_path"]

    def iter_files_in_directory(self, dir_path: str) -> Iterator[Tuple[Dict[str, Any], None]]:
        # dir_path comes from iter_dirs, already in forward-slash DB format
        # but also handle backslash paths gracefully
        dir_path_db = dir_path.replace("\\", "/")

        cur = self._mf.db.conn.cursor()

        # Find the directory row — we need volume_id too
        cur.execute(
            "SELECT id FROM directories WHERE dir_path = ?",
            (dir_path_db,),
        )
        dir_row = cur.fetchone()
        if dir_row is None:
            return

        directory_id = dir_row["id"]

        cur.execute(
            """
            SELECT * FROM files
            WHERE directory_id = ?
            ORDER BY name, extension
            """,
            (directory_id,),
        )
        for row in cur.fetchall():
            yield dict(row), None

    def collect_full_record(self, dir_path: str, entry: Any, st: Any) -> Dict[str, Any]:
        # entry is already the full file dict from iter_files_in_directory
        rec = dict(entry)
        rec["dir_path"] = dir_path.replace("\\", "/")
        return rec

    def directory_fingerprint(self, dir_path: str) -> str:
        dir_path_db = dir_path.replace("\\", "/")

        cur = self._mf.db.conn.cursor()
        cur.execute(
            "SELECT id FROM directories WHERE dir_path = ?",
            (dir_path_db,),
        )
        dir_row = cur.fetchone()
        if dir_row is None:
            return "0:0"

        directory_id = dir_row["id"]

        cur.execute(
            """
            SELECT COUNT(*) as cnt, MAX(mtime_ns) as max_mt
            FROM files
            WHERE directory_id = ?
            """,
            (directory_id,),
        )
        row = cur.fetchone()
        count = row["cnt"] if row["cnt"] else 0
        max_mt = row["max_mt"] if row["max_mt"] else 0
        return f"{count}:{max_mt}"
