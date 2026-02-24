# mock_files
"""
This module wraps the fs_database with a system that emulates a file system for testing purposes.

You can use it to create a real fs_database or a mock file system. However, remember the subtle
differences between a file system and the file tracking database. The file tracking database retains
a record of all files it has seen, even if they have been deleted or renamed.

For example:
1. Create a file in real life
2. Scan the directory where the file lives - it will be added to the database with its last-seen timestamp
3. Delete the file in real life
4. Scan again - the file's record remains in the database

To create an fs_database that includes sightings of deleted files, you should:
1. Create a mock file object
2. Create the file you want in it
3. Scan it into the database
4. Delete the file
5. Scan the mock_file object into the database again

Mock file objects can be created from an fs_database SQLite file and also stored as one.
"""
import os
import fnmatch
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from ..fs_database import FSDatabase
from .file_record_builder import FileRecordBuilder

class MockFiles:
    ONE_SECOND_NS = 1_000_000_000

    def __init__(self, db_path):
        """
        Initialize the mock file system.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db = FSDatabase(db_path)
        self.cwd = None  # Current working directory

        # Counters for auto-generating volume defaults
        self._next_drive_letter = ord('C')  # Start at C, increment to D, E, etc.
        self._next_serial_number = 0x10000000  # Start at a reasonable hex value

        # Check if C drive is mounted by looking at the volumes table
        # A drive is considered "mounted" if its root_path is not NULL/blank
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT root_path
            FROM volumes
            WHERE root_path IS NOT NULL
              AND root_path != ''
              AND UPPER(SUBSTR(root_path, 1, 1)) = 'C'
            LIMIT 1
        """)
        c_drive = cursor.fetchone()

        if c_drive:
            # C drive is mounted, use it
            self.cwd = c_drive['root_path']
        else:
            # C drive not mounted, find the lowest lettered drive
            cursor.execute("""
                SELECT root_path
                FROM volumes
                WHERE root_path IS NOT NULL
                  AND root_path != ''
                ORDER BY UPPER(SUBSTR(root_path, 1, 1))
                LIMIT 1
            """)
            lowest_drive = cursor.fetchone()

            if lowest_drive:
                self.cwd = lowest_drive['root_path']
            else:
                # No mounted drives found, default to C:\
                self.cwd = "C:\\"

        # Initialize the file record builder for managing file defaults
        self._file_builder = FileRecordBuilder()

        # Mock clock: auto-advances by 1 second on each filesystem-modifying operation
        self._current_time_ns = self._file_builder.parse_time("2025-01-01 00:00:00")

    # =========================================================================
    # Mock Clock
    # =========================================================================

    def get_time(self) -> int:
        """Return current mock clock time in nanoseconds."""
        return self._current_time_ns

    def set_time(self, time_value) -> None:
        """
        Set mock clock. Accepts nanoseconds (int) or human-readable string.

        Args:
            time_value: Nanoseconds (int) or parseable time string/datetime object.
        """
        self._current_time_ns = self._file_builder.parse_time(time_value)

    def increment_time(self, nanoseconds: int) -> None:
        """
        Advance mock clock by the given number of nanoseconds.

        Args:
            nanoseconds: Number of nanoseconds to advance.
        """
        self._current_time_ns += nanoseconds

    def _advance_time(self) -> None:
        """Internal: advance clock by 1 second."""
        self._current_time_ns += self.ONE_SECOND_NS

    def mount_volume(self, drive_letter=None, label=None, filesystem=None, serial_number=None):
        """
        Add/mount a new volume to the mock file system.

        Args:
            drive_letter: Drive letter (e.g., 'C', 'D'). If None, auto-generates next available.
            label: Human-readable volume label. If None, defaults to "Volume_X".
            filesystem: Filesystem type. If None, defaults to "NTFS".
            serial_number: Hex serial number string. If None, auto-generates.

        Returns:
            int: The volume ID from the database
        """
        # Generate drive letter if not provided
        if drive_letter is None:
            drive_letter = chr(self._next_drive_letter)
            self._next_drive_letter += 1
        else:
            drive_letter = drive_letter.upper()

        # Generate serial number if not provided
        if serial_number is None:
            serial_number = f"{self._next_serial_number:08X}"
            self._next_serial_number += 1

        # Set filesystem default
        if filesystem is None:
            filesystem = "NTFS"

        # Set label default
        if label is None:
            label = f"Volume_{drive_letter}"

        # Build root_path
        root_path = f"{drive_letter}:\\"

        # Build volume_key
        volume_key = f"{serial_number}-{filesystem}"

        # Upsert to database
        volume_id = self.db.upsert_volume(
            volume_key=volume_key,
            root_path=root_path,
            label=label,
            filesystem=filesystem,
            serial_number=serial_number
        )

        return volume_id

    def getcwd(self):
        """
        Get the current working directory.

        Returns:
            str: The current working directory path
        """
        return self.cwd

    def _normalize_path(self, path):
        """
        Normalize a path, handling relative and absolute paths.
        Converts forward slashes to backslashes for Windows consistency.

        Args:
            path: Path to normalize (can be relative or absolute)

        Returns:
            str: Normalized absolute path
        """
        # Convert to Windows-style backslashes
        path = path.replace('/', '\\')

        # If absolute path, return normalized version
        if len(path) >= 2 and path[1] == ':':
            # Normalize and ensure trailing backslash for root
            normalized = os.path.normpath(path)
            if len(normalized) == 2 and normalized[1] == ':':
                normalized += '\\'
            return normalized

        # Relative path - combine with cwd
        if self.cwd is None:
            raise ValueError("Current working directory is not set")

        combined = os.path.join(self.cwd, path)
        return os.path.normpath(combined)

    def _get_volume_id_for_path(self, path):
        """
        Get the volume ID for a given path by matching the drive letter.

        Args:
            path: Absolute path

        Returns:
            int: Volume ID, or None if not found

        Raises:
            ValueError: If path doesn't have a drive letter
        """
        if len(path) < 2 or path[1] != ':':
            raise ValueError(f"Path must be absolute with drive letter: {path}")

        drive_letter = path[0].upper()
        root_path = f"{drive_letter}:\\"

        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT id FROM volumes
            WHERE root_path = ?
        """, (root_path,))
        row = cursor.fetchone()

        return row['id'] if row else None

    def cd(self, path):
        """
        Change the current working directory.

        Args:
            path: Path to change to (can be relative or absolute)

        Raises:
            ValueError: If directory doesn't exist in the database
        """
        abs_path = self._normalize_path(path)

        # Check if it's a root directory (just the drive)
        if len(abs_path) == 3 and abs_path[1] == ':' and abs_path[2] == '\\':
            # Root directory - just check if volume exists
            volume_id = self._get_volume_id_for_path(abs_path)
            if volume_id is None:
                raise ValueError(f"Volume not mounted: {abs_path}")
            self.cwd = abs_path
            return

        # Check if directory exists in database
        volume_id = self._get_volume_id_for_path(abs_path)
        if volume_id is None:
            raise ValueError(f"Volume not mounted: {abs_path}")

        # Convert to forward slashes for database lookup
        dir_path_db = abs_path.replace('\\', '/')

        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT id FROM directories
            WHERE volume_id = ? AND dir_path = ?
        """, (volume_id, dir_path_db))
        row = cursor.fetchone()

        if row is None:
            raise ValueError(f"Directory does not exist: {abs_path}")

        self.cwd = abs_path

    def mkdir(self, path, parents=True):
        """
        Create a directory (and optionally parent directories).

        Args:
            path: Path to create (can be relative or absolute)
            parents: If True, create parent directories as needed (like mkdir -p)

        Raises:
            ValueError: If parents=False and parent doesn't exist
        """
        abs_path = self._normalize_path(path)

        # Get volume ID
        volume_id = self._get_volume_id_for_path(abs_path)
        if volume_id is None:
            raise ValueError(f"Volume not mounted: {abs_path}")

        # Convert to forward slashes for database
        dir_path_db = abs_path.replace('\\', '/')

        if parents:
            # Create all parent directories if they don't exist
            # Split path into parts
            parts = []
            current = abs_path
            while True:
                parent = os.path.dirname(current)
                if parent == current:  # Reached root
                    break
                parts.append(current)
                current = parent

            # Create directories from root to target
            for dir_to_create in reversed(parts):
                dir_path_db_current = dir_to_create.replace('\\', '/')

                # Check if already exists
                cursor = self.db.conn.cursor()
                cursor.execute("""
                    SELECT id FROM directories
                    WHERE volume_id = ? AND dir_path = ?
                """, (volume_id, dir_path_db_current))

                if cursor.fetchone() is None:
                    # Create it
                    self.db.upsert_directory(volume_id, dir_path_db_current)
        else:
            # Just create the directory (will fail if parent doesn't exist)
            parent_path = os.path.dirname(abs_path)
            parent_path_db = parent_path.replace('\\', '/')

            # Check if parent exists (unless it's root)
            if len(parent_path) > 3:
                cursor = self.db.conn.cursor()
                cursor.execute("""
                    SELECT id FROM directories
                    WHERE volume_id = ? AND dir_path = ?
                """, (volume_id, parent_path_db))

                if cursor.fetchone() is None:
                    raise ValueError(f"Parent directory does not exist: {parent_path}")

            # Create the directory
            self.db.upsert_directory(volume_id, dir_path_db)

        self._advance_time()

    def rmdir(self, path):
        """
        Remove a directory from the database.

        Args:
            path: Path to remove (can be relative or absolute)

        Raises:
            ValueError: If directory doesn't exist or is not empty
        """
        abs_path = self._normalize_path(path)

        # Get volume ID
        volume_id = self._get_volume_id_for_path(abs_path)
        if volume_id is None:
            raise ValueError(f"Volume not mounted: {abs_path}")

        # Convert to forward slashes for database
        dir_path_db = abs_path.replace('\\', '/')

        # Check if directory exists
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT id FROM directories
            WHERE volume_id = ? AND dir_path = ?
        """, (volume_id, dir_path_db))
        row = cursor.fetchone()

        if row is None:
            raise ValueError(f"Directory does not exist: {abs_path}")

        dir_id = row['id']

        # Check if directory has any files
        cursor.execute("""
            SELECT COUNT(*) as count FROM files
            WHERE directory_id = ?
        """, (dir_id,))
        file_count = cursor.fetchone()['count']

        if file_count > 0:
            raise ValueError(f"Directory not empty: {abs_path}")

        # Check if directory has any subdirectories
        cursor.execute("""
            SELECT COUNT(*) as count FROM directories
            WHERE volume_id = ? AND dir_path LIKE ?
        """, (volume_id, dir_path_db + '/%'))
        subdir_count = cursor.fetchone()['count']

        if subdir_count > 0:
            raise ValueError(f"Directory not empty (has subdirectories): {abs_path}")

        # Delete the directory
        cursor.execute("""
            DELETE FROM directories
            WHERE id = ?
        """, (dir_id,))
        self.db.conn.commit()
        self._advance_time()

    def set_file_defaults(self, **kwargs) -> None:
        """
        Set default values for file parameters.

        These defaults are used when creating files with save() if a parameter
        is not explicitly provided. Special parameters default_date and default_time
        control what date/time is used when only partial time info is provided.

        Args:
            **kwargs: Parameter names and their default values.
                File parameters: extension, size_bytes, mtime, ctime, size_on_disk,
                    readonly, system, is_symlink, presence_state
                Media parameters: duration, bitrate, codec, framerate, image_format,
                    resolution_width, resolution_height, sample_rate, channels
                Tag parameters: tag_title, tag_artist, tag_album, tag_album_artist,
                    tag_track, tag_date
                Special parameters: default_date, default_time

        Raises:
            ValueError: If an unknown parameter name is provided

        Example:
            mock_fs.set_file_defaults(extension='txt', size_bytes=1024)
            mock_fs.set_file_defaults(default_date='2024-01-01', default_time='12:00:00')
        """
        self._file_builder.set_defaults(**kwargs)

    def get_file_defaults(self) -> Dict[str, Any]:
        """
        Get a copy of the current file defaults.

        Returns:
            dict: Copy of the defaults dictionary
        """
        return self._file_builder.get_defaults()

    def save(
        self,
        name: str,
        extension: Optional[str] = None,
        **kwargs
    ) -> int:
        """
        Create/save a file in the current working directory.

        The name can include an extension (e.g., "document.txt") or be just a name
        (e.g., "document"). If the name has no extension, the default extension is used.
        If name has extension AND extension parameter is also provided, raises an error.

        When you specify a parameter, it both gets used for this file AND updates
        the default for future files.

        Time parameters (mtime, ctime) accept human-readable formats:
        - datetime objects
        - ISO format strings ("2024-01-15 10:30:00")
        - Date-only strings ("2024-01-15") - uses default_time
        - Time-only strings ("10:30:00") - uses default_date

        Args:
            name: Filename (required). Can include extension or not.
            extension: Optional explicit extension. Use '' for no extension.
                       Cannot be specified if name already has an extension.
            **kwargs: Other file parameters (size_bytes, mtime, ctime, readonly, etc.)

        Returns:
            int: The file ID from the database

        Raises:
            ValueError: If name has extension AND extension parameter is set,
                       or if an unknown parameter is provided,
                       or if the current directory doesn't exist.

        Example:
            # Create file with extension from name
            mock_fs.save("document.txt", size_bytes=1024)

            # Create file with explicit extension (becomes new default)
            mock_fs.save("readme", extension="md")

            # Create file with no extension
            mock_fs.save("Makefile", extension='')

            # Create file with time
            mock_fs.save("log.txt", mtime="2024-01-15 10:30:00")
        """
        # Build the file record (this also updates defaults)
        from .file_record_builder import _NOT_PROVIDED

        if extension is None:
            record = self._file_builder.build_record(name, **kwargs)
        else:
            record = self._file_builder.build_record(name, extension=extension, **kwargs)

        # Fill in mock clock time where sticky defaults are unset (None)
        if record['mtime_ns'] is None:
            record['mtime_ns'] = self._current_time_ns
        if record['ctime_ns'] is None:
            record['ctime_ns'] = self._current_time_ns

        # Get the directory ID for cwd
        dir_id = self._get_cwd_directory_id()

        # Insert into database
        file_id = self.db.upsert_file_record(dir_id, record)

        self._advance_time()
        return file_id

    # Media type classifications
    AUDIO_EXTENSIONS = frozenset(['mp3', 'wav', 'flac', 'aac', 'ogg', 'wma', 'm4a', 'opus', 'aiff', 'aif'])
    VIDEO_EXTENSIONS = frozenset(['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'mpeg', 'mpg'])
    IMAGE_EXTENSIONS = frozenset(['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp', 'svg', 'ico'])

    def save_m(
        self,
        name: str,
        extension: Optional[str] = None,
        tolerance: float = 0.05,
        **kwargs
    ) -> int:
        """
        Create/save a media file with automatic attribute computation.

        Works like save() but for media files (audio, video, images). If given
        partial attributes, computes missing ones where possible. If given
        conflicting values, raises an error.

        Relationships used for computation:
        - Audio/Video: size_bytes = duration * bitrate / 8
        - Given any 2 of (size_bytes, duration, bitrate), computes the 3rd

        Args:
            name: Filename (required). Can include extension or not.
            extension: Optional explicit extension.
            tolerance: Allowed relative difference for conflict detection (default 5%).
                       Set to 0 for exact matching.
            **kwargs: Media parameters:
                - duration: Length in seconds
                - bitrate: Bits per second
                - size_bytes: File size in bytes
                - codec: Codec name (e.g., 'mp3', 'h264')
                - sample_rate: Audio sample rate in Hz
                - channels: Number of audio channels
                - framerate: Video frame rate (fps)
                - resolution_width, resolution_height: Video/image dimensions
                - image_format: Image format string
                - Plus all standard file parameters (mtime, ctime, readonly, etc.)

        Returns:
            int: The file ID from the database

        Raises:
            ValueError: If attributes conflict (e.g., size != duration * bitrate / 8)
                       or if extension is not a recognized media type when computing.

        Example:
            # Compute size from duration and bitrate
            mock_fs.save_m("song.mp3", duration=180, bitrate=320000)
            # size_bytes will be computed as 180 * 320000 / 8 = 7,200,000

            # Compute duration from size and bitrate
            mock_fs.save_m("track.mp3", size_bytes=4800000, bitrate=320000)
            # duration will be computed as 4800000 * 8 / 320000 = 120 seconds

            # All three provided - will check for conflicts
            mock_fs.save_m("audio.mp3", size_bytes=7200000, duration=180, bitrate=320000)
            # OK - values are consistent

            # Conflicting values - raises error
            mock_fs.save_m("bad.mp3", size_bytes=1000, duration=180, bitrate=320000)
            # ValueError: size_bytes conflict: expected 7200000, got 1000
        """
        # Parse the extension to determine media type
        from .file_record_builder import _NOT_PROVIDED

        # Get extension from name or parameter
        if extension is not None:
            ext = extension.lower()
        elif '.' in name and not name.startswith('.'):
            ext = name.rsplit('.', 1)[1].lower()
        elif name.startswith('.') and '.' in name[1:]:
            ext = name.rsplit('.', 1)[1].lower()
        else:
            ext = self._file_builder._defaults.get('extension', '')

        # Extract media-related kwargs
        duration = kwargs.get('duration')
        bitrate = kwargs.get('bitrate')
        size_bytes = kwargs.get('size_bytes')

        # Determine media type and compute missing values
        is_audio = ext in self.AUDIO_EXTENSIONS
        is_video = ext in self.VIDEO_EXTENSIONS
        is_image = ext in self.IMAGE_EXTENSIONS

        if is_audio or is_video:
            # Compute missing values from the relationship: size = duration * bitrate / 8
            provided = sum(x is not None for x in [duration, bitrate, size_bytes])

            if provided == 2:
                # Can compute the missing one
                if size_bytes is None and duration is not None and bitrate is not None:
                    size_bytes = int(duration * bitrate / 8)
                    kwargs['size_bytes'] = size_bytes
                elif duration is None and size_bytes is not None and bitrate is not None:
                    duration = (size_bytes * 8) / bitrate
                    kwargs['duration'] = duration
                elif bitrate is None and size_bytes is not None and duration is not None:
                    if duration > 0:
                        bitrate = int((size_bytes * 8) / duration)
                        kwargs['bitrate'] = bitrate
                    else:
                        raise ValueError("Cannot compute bitrate: duration must be > 0")

            elif provided == 3:
                # All three provided - check for conflicts
                expected_size = duration * bitrate / 8

                # Check if values are consistent within tolerance
                if size_bytes > 0:
                    relative_diff = abs(expected_size - size_bytes) / size_bytes
                else:
                    relative_diff = abs(expected_size - size_bytes)

                if relative_diff > tolerance:
                    raise ValueError(
                        f"size_bytes conflict: expected {int(expected_size)} "
                        f"(duration={duration} * bitrate={bitrate} / 8), got {size_bytes}. "
                        f"Difference: {relative_diff:.1%} exceeds tolerance {tolerance:.1%}"
                    )

        # For images, we can't compute size from dimensions alone (depends on compression)
        # but we can validate that dimensions are set together
        if is_image:
            width = kwargs.get('resolution_width')
            height = kwargs.get('resolution_height')
            if (width is None) != (height is None):
                raise ValueError(
                    "For images, resolution_width and resolution_height must both be set or both be unset"
                )

        # Now call save with the potentially updated kwargs
        if extension is None:
            return self.save(name, **kwargs)
        else:
            return self.save(name, extension=extension, **kwargs)

    def _get_cwd_directory_id(self) -> int:
        """
        Get the directory ID for the current working directory.

        If cwd is a root directory, creates/gets a directory entry for it.

        Returns:
            int: Directory ID

        Raises:
            ValueError: If volume is not mounted
        """
        if self.cwd is None:
            raise ValueError("Current working directory is not set")

        abs_path = self._normalize_path(self.cwd)
        volume_id = self._get_volume_id_for_path(abs_path)

        if volume_id is None:
            raise ValueError(f"Volume not mounted: {abs_path}")

        # Convert to forward slashes for database
        dir_path_db = abs_path.replace('\\', '/')

        # For root directory, we need to ensure a directory entry exists
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT id FROM directories
            WHERE volume_id = ? AND dir_path = ?
        """, (volume_id, dir_path_db))
        row = cursor.fetchone()

        if row is None:
            # Create the directory entry
            dir_id = self.db.upsert_directory(volume_id, dir_path_db)
        else:
            dir_id = row['id']

        return dir_id

    def ls(self) -> List[Dict[str, Any]]:
        """
        List all files in the current working directory.

        Returns information about all files (not directories) in the current
        directory. Does not recurse into subdirectories.

        Returns:
            list: List of dictionaries, each containing all file information:
                - name: File name without extension
                - extension: File extension (lowercase, no dot)
                - size_bytes: File size in bytes
                - mtime_ns: Modification time in nanoseconds since epoch
                - ctime_ns: Creation time in nanoseconds since epoch
                - size_on_disk: Size on disk in bytes
                - readonly: 1 if read-only, 0 otherwise
                - system: 1 if system file, 0 otherwise
                - is_symlink: 1 if symlink, 0 otherwise
                - presence_state: 0=PRESENT, 1=PENDING_SCAN, 2=MISSING
                - (plus media and tag fields if present)

        Example:
            files = mock_fs.ls()
            for f in files:
                print(f"{f['name']}.{f['extension']}: {f['size_bytes']} bytes")
        """
        if self.cwd is None:
            return []

        abs_path = self._normalize_path(self.cwd)
        volume_id = self._get_volume_id_for_path(abs_path)

        if volume_id is None:
            return []

        dir_path_db = abs_path.replace('\\', '/')

        cursor = self.db.conn.cursor()

        # Get directory ID
        cursor.execute("""
            SELECT id FROM directories
            WHERE volume_id = ? AND dir_path = ?
        """, (volume_id, dir_path_db))
        row = cursor.fetchone()

        if row is None:
            return []

        dir_id = row['id']

        # Get all files in this directory
        cursor.execute("""
            SELECT * FROM files
            WHERE directory_id = ?
            ORDER BY name, extension
        """, (dir_id,))

        files = []
        for row in cursor.fetchall():
            file_dict = dict(row)
            files.append(file_dict)

        return files

    def ls_dir(self) -> List[str]:
        """
        List all immediate subdirectories in the current working directory.

        Returns only direct children, not recursive. Returns directory names
        (not full paths).

        Returns:
            list: List of subdirectory names (just the directory name, not full path)

        Example:
            subdirs = mock_fs.ls_dir()
            # Returns: ['Documents', 'Downloads', 'Pictures']
        """
        if self.cwd is None:
            return []

        abs_path = self._normalize_path(self.cwd)
        volume_id = self._get_volume_id_for_path(abs_path)

        if volume_id is None:
            return []

        dir_path_db = abs_path.replace('\\', '/')

        # Find all directories that are immediate children
        # They should have dir_path that starts with current path + '/'
        # but should NOT have any additional '/' after that
        cursor = self.db.conn.cursor()

        if dir_path_db.endswith('/'):
            prefix = dir_path_db
        else:
            prefix = dir_path_db + '/'

        cursor.execute("""
            SELECT dir_path FROM directories
            WHERE volume_id = ?
              AND dir_path LIKE ?
              AND dir_path NOT LIKE ?
            ORDER BY dir_path
        """, (volume_id, prefix + '%', prefix + '%/%'))

        subdirs = []
        for row in cursor.fetchall():
            # Extract just the directory name from the full path
            full_path = row['dir_path']
            # Remove the prefix to get just the subdirectory name
            subdir_name = full_path[len(prefix):]
            if subdir_name:  # Make sure it's not empty
                subdirs.append(subdir_name)

        return subdirs

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _resolve_path(self, path: str) -> Tuple[int, str, str, str]:
        """
        Parse a full path into components.

        Args:
            path: Path to parse (can be relative or absolute)

        Returns:
            tuple: (volume_id, dir_path_db, filename, extension)
                - volume_id: ID of the volume
                - dir_path_db: Directory path in database format (forward slashes)
                - filename: Name without extension
                - extension: File extension (lowercase, no dot)

        Raises:
            ValueError: If volume is not mounted or path is invalid
        """
        abs_path = self._normalize_path(path)
        volume_id = self._get_volume_id_for_path(abs_path)

        if volume_id is None:
            raise ValueError(f"Volume not mounted: {abs_path}")

        # Split directory from filename
        dir_part = os.path.dirname(abs_path)
        filename_full = os.path.basename(abs_path)

        # Parse filename and extension
        if '.' in filename_full and not filename_full.startswith('.'):
            parts = filename_full.rsplit('.', 1)
            filename = parts[0]
            extension = parts[1].lower()
        elif filename_full.startswith('.') and '.' in filename_full[1:]:
            # Hidden file with extension like .config.json
            parts = filename_full.rsplit('.', 1)
            filename = parts[0]
            extension = parts[1].lower()
        else:
            filename = filename_full
            extension = ''

        # Convert directory to database format
        dir_path_db = dir_part.replace('\\', '/')

        return volume_id, dir_path_db, filename, extension

    def _get_file_id(self, path: str) -> Optional[int]:
        """
        Resolve path to file ID in database.

        Args:
            path: Path to the file (can be relative or absolute)

        Returns:
            int: File ID if found, None if file doesn't exist
        """
        try:
            volume_id, dir_path_db, filename, extension = self._resolve_path(path)
        except ValueError:
            return None

        cursor = self.db.conn.cursor()

        # Get directory ID
        cursor.execute("""
            SELECT id FROM directories
            WHERE volume_id = ? AND dir_path = ?
        """, (volume_id, dir_path_db))
        dir_row = cursor.fetchone()

        if dir_row is None:
            return None

        # Get file ID
        cursor.execute("""
            SELECT id FROM files
            WHERE directory_id = ? AND name = ? AND extension = ?
        """, (dir_row['id'], filename, extension))
        file_row = cursor.fetchone()

        return file_row['id'] if file_row else None

    def _expand_wildcards(self, pattern: str) -> List[str]:
        """
        Use fnmatch to match files against a pattern.

        Args:
            pattern: Pattern with wildcards (e.g., "*.txt", "file?.*")
                     Can be absolute path or relative to cwd

        Returns:
            List of matching absolute paths (backslash format)
        """
        abs_pattern = self._normalize_path(pattern)

        # Split into directory and filename pattern
        dir_part = os.path.dirname(abs_pattern)
        file_pattern = os.path.basename(abs_pattern)

        # If no wildcards, just return the pattern if it exists
        if '*' not in file_pattern and '?' not in file_pattern and '[' not in file_pattern:
            if self._get_file_id(abs_pattern) is not None:
                return [abs_pattern]
            return []

        # Get volume ID
        volume_id = self._get_volume_id_for_path(dir_part)
        if volume_id is None:
            return []

        # Convert directory to database format
        dir_path_db = dir_part.replace('\\', '/')

        # Get directory ID
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT id FROM directories
            WHERE volume_id = ? AND dir_path = ?
        """, (volume_id, dir_path_db))
        dir_row = cursor.fetchone()

        if dir_row is None:
            return []

        # Get all files in this directory
        cursor.execute("""
            SELECT name, extension FROM files
            WHERE directory_id = ?
        """, (dir_row['id'],))

        matches = []
        for row in cursor.fetchall():
            # Reconstruct filename
            if row['extension']:
                filename = f"{row['name']}.{row['extension']}"
            else:
                filename = row['name']

            # Check if it matches the pattern
            if fnmatch.fnmatch(filename, file_pattern):
                full_path = os.path.join(dir_part, filename)
                matches.append(full_path)

        return matches

    def _get_directory_id(self, path: str) -> Optional[int]:
        """
        Get directory ID for a given path.

        Args:
            path: Path to the directory (can be relative or absolute)

        Returns:
            int: Directory ID if found, None if doesn't exist
        """
        abs_path = self._normalize_path(path)
        volume_id = self._get_volume_id_for_path(abs_path)

        if volume_id is None:
            return None

        dir_path_db = abs_path.replace('\\', '/')

        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT id FROM directories
            WHERE volume_id = ? AND dir_path = ?
        """, (volume_id, dir_path_db))
        row = cursor.fetchone()

        return row['id'] if row else None

    # =========================================================================
    # File Operations
    # =========================================================================

    def exists(self, path: str) -> bool:
        """
        Check if a file or directory exists.

        Args:
            path: Path to check (can be relative or absolute)

        Returns:
            bool: True if file or directory exists, False otherwise
        """
        abs_path = self._normalize_path(path)

        # Check if it's a file
        if self._get_file_id(abs_path) is not None:
            return True

        # Check if it's a directory
        if self._get_directory_id(abs_path) is not None:
            return True

        # Check if it's the root of a mounted volume
        if len(abs_path) == 3 and abs_path[1] == ':' and abs_path[2] == '\\':
            volume_id = self._get_volume_id_for_path(abs_path)
            return volume_id is not None

        return False

    def get_file(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Get file record by path.

        Args:
            path: Path to the file (can be relative or absolute)

        Returns:
            dict: Dictionary of all file fields, or None if not found
        """
        try:
            volume_id, dir_path_db, filename, extension = self._resolve_path(path)
        except ValueError:
            return None

        cursor = self.db.conn.cursor()

        # Get directory ID
        cursor.execute("""
            SELECT id FROM directories
            WHERE volume_id = ? AND dir_path = ?
        """, (volume_id, dir_path_db))
        dir_row = cursor.fetchone()

        if dir_row is None:
            return None

        # Get file record
        cursor.execute("""
            SELECT * FROM files
            WHERE directory_id = ? AND name = ? AND extension = ?
        """, (dir_row['id'], filename, extension))
        file_row = cursor.fetchone()

        if file_row is None:
            return None

        return dict(file_row)

    def delete(self, path: str) -> bool:
        """
        Delete a file from the database.

        Args:
            path: Path to the file (can be relative or absolute)

        Returns:
            bool: True if deleted, False if not found
        """
        file_id = self._get_file_id(path)

        if file_id is None:
            return False

        cursor = self.db.conn.cursor()
        cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
        self.db.conn.commit()

        self._advance_time()
        return True

    # Alias for delete
    rm = delete

    def set_attributes(self, path: str, **kwargs) -> bool:
        """
        Modify attributes of an existing file.

        Args:
            path: Path to the file (can be relative or absolute)
            **kwargs: Attributes to modify. Valid attributes are:
                size_bytes, mtime, ctime, size_on_disk, readonly, system,
                is_symlink, presence_state, duration, bitrate, codec,
                framerate, image_format, resolution_width, resolution_height,
                sample_rate, channels, tag_title, tag_artist, tag_album,
                tag_album_artist, tag_track, tag_date

        Returns:
            bool: True if updated, False if file not found

        Raises:
            ValueError: If an invalid attribute name is provided
        """
        from .file_record_builder import FileRecordBuilder

        # Validate kwargs
        valid_attrs = FileRecordBuilder.VALID_PARAMS - {'extension'}  # Can't change extension
        for key in kwargs:
            if key not in valid_attrs:
                raise ValueError(f"Invalid attribute: {key}")

        file_id = self._get_file_id(path)
        if file_id is None:
            return False

        if not kwargs:
            return True  # Nothing to update

        # Build SET clause
        set_parts = []
        values = []

        for key, value in kwargs.items():
            # Handle time conversion
            if key in ('mtime', 'ctime'):
                db_key = f'{key}_ns'
                if value is not None:
                    value = self._file_builder.parse_time(value)
            else:
                db_key = key

            set_parts.append(f"{db_key} = ?")
            values.append(value)

        values.append(file_id)

        cursor = self.db.conn.cursor()
        cursor.execute(f"""
            UPDATE files
            SET {', '.join(set_parts)}
            WHERE id = ?
        """, values)
        self.db.conn.commit()

        self._advance_time()
        return True

    def find(self, pattern: str, path: str = None, recursive: bool = True) -> List[str]:
        """
        Find files matching fnmatch pattern.

        Args:
            pattern: fnmatch pattern (e.g., "*.txt", "file?.*", "[abc]*")
            path: Directory to search in (defaults to cwd)
            recursive: If True, search subdirectories. If False, only specified dir.

        Returns:
            List of matching absolute paths (backslash format)
        """
        if path is None:
            search_path = self.cwd
        else:
            search_path = self._normalize_path(path)

        volume_id = self._get_volume_id_for_path(search_path)
        if volume_id is None:
            return []

        search_path_db = search_path.replace('\\', '/')

        # Build LIKE pattern - handle root directory case
        if search_path_db.endswith('/'):
            like_pattern = search_path_db + '%'
        else:
            like_pattern = search_path_db + '/%'

        cursor = self.db.conn.cursor()

        if recursive:
            # Get all directories that start with search_path
            cursor.execute("""
                SELECT id, dir_path FROM directories
                WHERE volume_id = ?
                  AND (dir_path = ? OR dir_path LIKE ?)
            """, (volume_id, search_path_db, like_pattern))
        else:
            # Only the specified directory
            cursor.execute("""
                SELECT id, dir_path FROM directories
                WHERE volume_id = ? AND dir_path = ?
            """, (volume_id, search_path_db))

        dir_rows = cursor.fetchall()
        matches = []

        for dir_row in dir_rows:
            dir_id = dir_row['id']
            dir_path = dir_row['dir_path']

            # Get all files in this directory
            cursor.execute("""
                SELECT name, extension FROM files
                WHERE directory_id = ?
            """, (dir_id,))

            for file_row in cursor.fetchall():
                # Reconstruct filename
                if file_row['extension']:
                    filename = f"{file_row['name']}.{file_row['extension']}"
                else:
                    filename = file_row['name']

                # Check if it matches the pattern
                if fnmatch.fnmatch(filename, pattern):
                    # Convert to backslash path
                    full_path = dir_path.replace('/', '\\') + '\\' + filename
                    matches.append(full_path)

        return sorted(matches)

    def copy(self, source: str, dest: str, preserve_timestamps: bool = True) -> int:
        """
        Copy file(s) to destination.

        Supports wildcards in source pattern.

        Args:
            source: Source file path or pattern with wildcards
            dest: Destination path (file or directory)
            preserve_timestamps: If True, preserve mtime/ctime. If False, use current defaults.

        Returns:
            int: Count of files copied
        """
        # Expand wildcards
        source_files = self._expand_wildcards(source)

        if not source_files:
            return 0

        # Determine if dest is a directory
        dest_abs = self._normalize_path(dest)
        dest_is_dir = self._get_directory_id(dest_abs) is not None

        # If multiple files, dest must be a directory
        if len(source_files) > 1 and not dest_is_dir:
            raise ValueError("Destination must be a directory when copying multiple files")

        count = 0
        for src_path in source_files:
            # Get source file record
            src_record = self.get_file(src_path)
            if src_record is None:
                continue

            # Determine destination path
            if dest_is_dir:
                src_filename = os.path.basename(src_path)
                dest_path = os.path.join(dest_abs, src_filename)
            else:
                dest_path = dest_abs

            # Parse destination
            volume_id, dir_path_db, filename, extension = self._resolve_path(dest_path)

            # Get or create destination directory
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT id FROM directories
                WHERE volume_id = ? AND dir_path = ?
            """, (volume_id, dir_path_db))
            dir_row = cursor.fetchone()

            if dir_row is None:
                # Create directory
                self.mkdir(dir_path_db.replace('/', '\\'))
                cursor.execute("""
                    SELECT id FROM directories
                    WHERE volume_id = ? AND dir_path = ?
                """, (volume_id, dir_path_db))
                dir_row = cursor.fetchone()

            dir_id = dir_row['id']

            # Build new record
            new_record = {
                'name': filename,
                'extension': extension,
                'size_bytes': src_record['size_bytes'],
                'size_on_disk': src_record['size_on_disk'],
                'readonly': src_record['readonly'],
                'system': src_record['system'],
                'is_symlink': src_record['is_symlink'],
                'presence_state': src_record['presence_state'],
                # Media fields
                'duration': src_record.get('duration'),
                'bitrate': src_record.get('bitrate'),
                'codec': src_record.get('codec'),
                'framerate': src_record.get('framerate'),
                'image_format': src_record.get('image_format'),
                'resolution_width': src_record.get('resolution_width'),
                'resolution_height': src_record.get('resolution_height'),
                'sample_rate': src_record.get('sample_rate'),
                'channels': src_record.get('channels'),
                # Tag fields
                'tag_title': src_record.get('tag_title'),
                'tag_artist': src_record.get('tag_artist'),
                'tag_album': src_record.get('tag_album'),
                'tag_album_artist': src_record.get('tag_album_artist'),
                'tag_track': src_record.get('tag_track'),
                'tag_date': src_record.get('tag_date'),
            }

            if preserve_timestamps:
                new_record['mtime_ns'] = src_record.get('mtime_ns')
                new_record['ctime_ns'] = src_record.get('ctime_ns')
            else:
                # Use current defaults; fall back to mock clock if unset
                mtime = self._file_builder._defaults.get('mtime')
                ctime = self._file_builder._defaults.get('ctime')
                new_record['mtime_ns'] = self._file_builder.parse_time(mtime) if mtime is not None else self._current_time_ns
                new_record['ctime_ns'] = self._file_builder.parse_time(ctime) if ctime is not None else self._current_time_ns

            # Insert into database
            self.db.upsert_file_record(dir_id, new_record)
            count += 1

        self._advance_time()
        return count

    def move(self, source: str, dest: str) -> int:
        """
        Move/rename file(s).

        Supports wildcards in source pattern.

        Args:
            source: Source file path or pattern with wildcards
            dest: Destination path (file or directory)

        Returns:
            int: Count of files moved
        """
        # Expand wildcards
        source_files = self._expand_wildcards(source)

        if not source_files:
            return 0

        # Determine if dest is a directory
        dest_abs = self._normalize_path(dest)
        dest_is_dir = self._get_directory_id(dest_abs) is not None

        # If multiple files, dest must be a directory
        if len(source_files) > 1 and not dest_is_dir:
            raise ValueError("Destination must be a directory when moving multiple files")

        count = 0
        cursor = self.db.conn.cursor()

        for src_path in source_files:
            file_id = self._get_file_id(src_path)
            if file_id is None:
                continue

            # Determine destination
            if dest_is_dir:
                src_filename = os.path.basename(src_path)
                dest_path = os.path.join(dest_abs, src_filename)
            else:
                dest_path = dest_abs

            # Parse destination
            volume_id, dir_path_db, new_name, new_extension = self._resolve_path(dest_path)

            # Get or create destination directory
            cursor.execute("""
                SELECT id FROM directories
                WHERE volume_id = ? AND dir_path = ?
            """, (volume_id, dir_path_db))
            dir_row = cursor.fetchone()

            if dir_row is None:
                # Create directory
                self.mkdir(dir_path_db.replace('/', '\\'))
                cursor.execute("""
                    SELECT id FROM directories
                    WHERE volume_id = ? AND dir_path = ?
                """, (volume_id, dir_path_db))
                dir_row = cursor.fetchone()

            new_dir_id = dir_row['id']

            # Update file record
            cursor.execute("""
                UPDATE files
                SET directory_id = ?, name = ?, extension = ?
                WHERE id = ?
            """, (new_dir_id, new_name, new_extension, file_id))

            count += 1

        self.db.conn.commit()
        self._advance_time()
        return count

    # =========================================================================
    # Directory Operations
    # =========================================================================

    def copydir(self, source: str, dest: str) -> int:
        """
        Copy directory recursively.

        Args:
            source: Source directory path
            dest: Destination directory path

        Returns:
            int: Count of files copied
        """
        source_abs = self._normalize_path(source)
        dest_abs = self._normalize_path(dest)

        # Verify source exists
        source_dir_id = self._get_directory_id(source_abs)
        if source_dir_id is None:
            raise ValueError(f"Source directory does not exist: {source}")

        volume_id = self._get_volume_id_for_path(source_abs)
        source_db = source_abs.replace('\\', '/')
        dest_db = dest_abs.replace('\\', '/')

        # Create destination directory
        self.mkdir(dest_abs)

        cursor = self.db.conn.cursor()

        # Get all subdirectories under source
        cursor.execute("""
            SELECT dir_path FROM directories
            WHERE volume_id = ? AND dir_path LIKE ?
        """, (volume_id, source_db + '/%'))

        # Create corresponding subdirectories in dest
        for row in cursor.fetchall():
            src_subdir = row['dir_path']
            # Replace source prefix with dest prefix
            relative_part = src_subdir[len(source_db):]
            dest_subdir = dest_db + relative_part
            self.mkdir(dest_subdir.replace('/', '\\'))

        # Get all files in source directory tree
        cursor.execute("""
            SELECT d.dir_path, f.*
            FROM files f
            JOIN directories d ON f.directory_id = d.id
            WHERE d.volume_id = ?
              AND (d.dir_path = ? OR d.dir_path LIKE ?)
        """, (volume_id, source_db, source_db + '/%'))

        count = 0
        dest_volume_id = self._get_volume_id_for_path(dest_abs)

        for row in cursor.fetchall():
            src_dir_path = row['dir_path']
            relative_part = src_dir_path[len(source_db):]
            dest_dir_path = dest_db + relative_part

            # Get destination directory ID
            cursor2 = self.db.conn.cursor()
            cursor2.execute("""
                SELECT id FROM directories
                WHERE volume_id = ? AND dir_path = ?
            """, (dest_volume_id, dest_dir_path))
            dest_dir_row = cursor2.fetchone()

            if dest_dir_row is None:
                continue

            # Build new record
            new_record = {
                'name': row['name'],
                'extension': row['extension'],
                'size_bytes': row['size_bytes'],
                'mtime_ns': row['mtime_ns'],
                'ctime_ns': row['ctime_ns'],
                'size_on_disk': row['size_on_disk'],
                'readonly': row['readonly'],
                'system': row['system'],
                'is_symlink': row['is_symlink'],
                'presence_state': row['presence_state'],
                'duration': row['duration'],
                'bitrate': row['bitrate'],
                'codec': row['codec'],
                'framerate': row['framerate'],
                'image_format': row['image_format'],
                'resolution_width': row['resolution_width'],
                'resolution_height': row['resolution_height'],
                'sample_rate': row['sample_rate'],
                'channels': row['channels'],
                'tag_title': row['tag_title'],
                'tag_artist': row['tag_artist'],
                'tag_album': row['tag_album'],
                'tag_album_artist': row['tag_album_artist'],
                'tag_track': row['tag_track'],
                'tag_date': row['tag_date'],
            }

            self.db.upsert_file_record(dest_dir_row['id'], new_record)
            count += 1

        self._advance_time()
        return count

    def movedir(self, source: str, dest: str) -> int:
        """
        Move/rename directory.

        Args:
            source: Source directory path
            dest: Destination directory path

        Returns:
            int: Count of directories/files affected
        """
        source_abs = self._normalize_path(source)
        dest_abs = self._normalize_path(dest)

        # Verify source exists
        volume_id = self._get_volume_id_for_path(source_abs)
        if volume_id is None:
            raise ValueError(f"Volume not mounted: {source_abs}")

        source_db = source_abs.replace('\\', '/')
        dest_db = dest_abs.replace('\\', '/')

        cursor = self.db.conn.cursor()

        # Check source exists
        cursor.execute("""
            SELECT id FROM directories
            WHERE volume_id = ? AND dir_path = ?
        """, (volume_id, source_db))

        if cursor.fetchone() is None:
            raise ValueError(f"Source directory does not exist: {source}")

        # Update all directory paths that start with source
        # First, get count for return value
        cursor.execute("""
            SELECT COUNT(*) as count FROM directories
            WHERE volume_id = ?
              AND (dir_path = ? OR dir_path LIKE ?)
        """, (volume_id, source_db, source_db + '/%'))
        count = cursor.fetchone()['count']

        # Update the directories
        # Use REPLACE to change the prefix
        cursor.execute("""
            UPDATE directories
            SET dir_path = ? || SUBSTR(dir_path, ?)
            WHERE volume_id = ?
              AND (dir_path = ? OR dir_path LIKE ?)
        """, (dest_db, len(source_db) + 1, volume_id, source_db, source_db + '/%'))

        self.db.conn.commit()

        self._advance_time()
        return count
