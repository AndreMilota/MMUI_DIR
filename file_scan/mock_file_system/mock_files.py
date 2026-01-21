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
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..fs_database import FSDatabase
from .file_record_builder import FileRecordBuilder

class MockFiles:
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

        # Get the directory ID for cwd
        dir_id = self._get_cwd_directory_id()

        # Insert into database
        file_id = self.db.upsert_file_record(dir_id, record)

        return file_id

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
