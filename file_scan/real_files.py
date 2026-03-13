# real_files.py
"""
RealFiles: A file system implementation that works with the actual filesystem.

Unlike MockFiles which operates on a virtual filesystem backed by SQLite,
RealFiles performs actual file operations on the real disk.

SAFETY: By default, allow_modifications is False, which means any operation
that would modify the filesystem will raise a PermissionError. You must
explicitly set allow_modifications=True to enable write operations.
"""
import os
import shutil
import fnmatch
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from .base_files import BaseFiles


class RealFiles(BaseFiles):
    """
    File system implementation that operates on the real filesystem.

    WARNING: This class can perform actual file operations. Use with caution.

    The allow_modifications flag (default False) prevents any write operations.
    Set allow_modifications=True to enable:
    - mkdir, rmdir
    - save, save_m
    - delete/rm
    - set_attributes
    - copy, move
    - copydir, movedir

    Read-only operations are always allowed:
    - getcwd, cd (changes internal cwd, not process cwd)
    - ls, ls_dir, dir
    - exists, get_file, find
    - can_change
    """

    ONE_SECOND_NS = 1_000_000_000

    def __init__(self, start_path: str = None, allow_modifications: bool = False):
        """
        Initialize RealFiles.

        Args:
            start_path: Initial working directory. Defaults to os.getcwd().
            allow_modifications: If False (default), write operations raise PermissionError.
                                 Must be explicitly set to True to allow modifications.
        """
        self.allow_modifications = allow_modifications
        self._file_defaults: Dict[str, Any] = {}

        if start_path is None:
            self.cwd = os.getcwd()
        else:
            self.cwd = os.path.abspath(start_path)
            if not os.path.isdir(self.cwd):
                raise ValueError(f"Start path does not exist or is not a directory: {start_path}")

    def _check_modifications_allowed(self) -> None:
        """Raise PermissionError if modifications are not allowed."""
        if not self.allow_modifications:
            raise PermissionError(
                "Filesystem modifications are disabled. "
                "Set allow_modifications=True to enable write operations."
            )

    def _normalize_path(self, path: str) -> str:
        """
        Normalize a path, handling relative and absolute paths.

        Args:
            path: Path to normalize (can be relative or absolute)

        Returns:
            str: Normalized absolute path
        """
        if os.path.isabs(path):
            return os.path.normpath(path)
        return os.path.normpath(os.path.join(self.cwd, path))

    # =========================================================================
    # Time Operations
    # =========================================================================

    def get_time(self) -> int:
        """Return current system time in nanoseconds."""
        return time.time_ns()

    def set_time(self, time_value) -> None:
        """
        No-op for RealFiles. Cannot set system time.

        Args:
            time_value: Ignored.
        """
        pass

    def increment_time(self, nanoseconds: int) -> None:
        """
        No-op for RealFiles. Time advances naturally.

        Args:
            nanoseconds: Ignored.
        """
        pass

    # =========================================================================
    # Volume/Mount Operations
    # =========================================================================

    def mount_volume(self, drive_letter=None, label=None, filesystem=None, serial_number=None) -> int:
        """
        No-op for RealFiles. Volumes are managed by the OS.

        Returns:
            int: Always returns 0
        """
        return 0

    # =========================================================================
    # Working Directory Operations
    # =========================================================================

    def getcwd(self) -> str:
        """Get the current working directory."""
        return self.cwd

    def cd(self, path: str) -> None:
        """
        Change the current working directory.

        Note: This changes the internal cwd, not the process working directory.

        Args:
            path: Path to change to (can be relative or absolute)

        Raises:
            ValueError: If directory doesn't exist
        """
        abs_path = self._normalize_path(path)
        if not os.path.isdir(abs_path):
            raise ValueError(f"Directory does not exist: {abs_path}")
        self.cwd = abs_path

    # =========================================================================
    # Directory Operations
    # =========================================================================

    def mkdir(self, path: str, parents: bool = True) -> None:
        """
        Create a directory (and optionally parent directories).

        Args:
            path: Path to create (can be relative or absolute)
            parents: If True, create parent directories as needed

        Raises:
            PermissionError: If allow_modifications is False
        """
        self._check_modifications_allowed()
        abs_path = self._normalize_path(path)
        if parents:
            os.makedirs(abs_path, exist_ok=True)
        else:
            os.mkdir(abs_path)

    def rmdir(self, path: str) -> None:
        """
        Remove a directory.

        Args:
            path: Path to remove (can be relative or absolute)

        Raises:
            PermissionError: If allow_modifications is False
            ValueError: If directory doesn't exist or is not empty
        """
        self._check_modifications_allowed()
        abs_path = self._normalize_path(path)
        if not os.path.isdir(abs_path):
            raise ValueError(f"Directory does not exist: {abs_path}")
        try:
            os.rmdir(abs_path)
        except OSError as e:
            raise ValueError(f"Directory not empty: {abs_path}") from e

    def ls(self) -> List[Dict[str, Any]]:
        """
        List all files in the current working directory.

        Returns:
            list: List of dictionaries containing file information
        """
        files = []
        try:
            for entry in os.scandir(self.cwd):
                if entry.is_file():
                    files.append(self._get_file_info(entry.path))
        except PermissionError:
            pass
        return files

    def ls_dir(self) -> List[str]:
        """
        List all immediate subdirectories in the current working directory.

        Returns:
            list: List of subdirectory names
        """
        subdirs = []
        try:
            for entry in os.scandir(self.cwd):
                if entry.is_dir():
                    subdirs.append(entry.name)
        except PermissionError:
            pass
        return sorted(subdirs)

    def dir(self, path: str = None) -> str:
        """
        List all files and subdirectories in the given directory.

        Args:
            path: Directory to list (defaults to cwd)

        Returns:
            str: Formatted multi-line string of directory contents
        """
        if path is None:
            target = self.cwd
        else:
            target = self._normalize_path(path)

        if not os.path.isdir(target):
            return f"dir: {target}\n  (directory not found)"

        lines = [f"dir: {target}"]
        subdirs = []
        files = []

        try:
            for entry in os.scandir(target):
                if entry.is_dir():
                    subdirs.append(entry.name)
                elif entry.is_file():
                    files.append(entry.name)
        except PermissionError:
            lines.append("  (permission denied)")
            return "\n".join(lines)

        subdirs.sort()
        files.sort()

        for d in subdirs:
            lines.append(f"  [{d}/]")
        for f in files:
            lines.append(f"  {f}")
        if not subdirs and not files:
            lines.append("  (empty)")

        return "\n".join(lines)

    def copydir(self, source: str, dest: str) -> int:
        """
        Copy directory recursively.

        Args:
            source: Source directory path
            dest: Destination directory path

        Returns:
            int: Count of files copied

        Raises:
            PermissionError: If allow_modifications is False
        """
        self._check_modifications_allowed()
        source_abs = self._normalize_path(source)
        dest_abs = self._normalize_path(dest)

        if not os.path.isdir(source_abs):
            raise ValueError(f"Source directory does not exist: {source}")

        # Count files
        count = sum(len(files) for _, _, files in os.walk(source_abs))

        shutil.copytree(source_abs, dest_abs)  # <------- FILE OPERATION: recursive copy
        return count

    def movedir(self, source: str, dest: str) -> int:
        """
        Move/rename directory.

        Args:
            source: Source directory path
            dest: Destination directory path

        Returns:
            int: Count of items in the moved directory

        Raises:
            PermissionError: If allow_modifications is False
        """
        self._check_modifications_allowed()
        source_abs = self._normalize_path(source)
        dest_abs = self._normalize_path(dest)

        if not os.path.isdir(source_abs):
            raise ValueError(f"Source directory does not exist: {source}")

        # Count items (dirs + files)
        count = sum(1 for _ in os.walk(source_abs))

        shutil.move(source_abs, dest_abs)  # <------- FILE OPERATION: move directory
        return count

    # =========================================================================
    # File Defaults
    # =========================================================================

    def set_file_defaults(self, **kwargs) -> None:
        """
        Set default values for file parameters when creating files.

        For RealFiles, this stores defaults but has limited use since
        most file attributes are determined by the filesystem.

        Args:
            **kwargs: Parameter names and their default values.
        """
        self._file_defaults.update(kwargs)

    def get_file_defaults(self) -> Dict[str, Any]:
        """Get a copy of the current file defaults."""
        return self._file_defaults.copy()

    # =========================================================================
    # File Creation Operations
    # =========================================================================

    def save(self, name: str, extension: Optional[str] = None, **kwargs) -> int:
        """
        Create/save a file in the current working directory.

        For RealFiles, this creates an empty file (or with content if provided).

        Args:
            name: Filename (required). Can include extension or not.
            extension: Optional explicit extension.
            **kwargs: May include 'content' to write to file.

        Returns:
            int: Always returns 0 (no database ID for real files)

        Raises:
            PermissionError: If allow_modifications is False
        """
        self._check_modifications_allowed()

        # Handle extension
        if extension is not None:
            if '.' in name and not name.startswith('.'):
                raise ValueError("Cannot specify extension when name already has one")
            filename = f"{name}.{extension}" if extension else name
        else:
            filename = name

        filepath = os.path.join(self.cwd, filename)
        content = kwargs.get('content', '')

        with open(filepath, 'w') as f:  # <------- FILE OPERATION: create file
            f.write(content)

        return 0

    def save_m(self, name: str, extension: Optional[str] = None,
               tolerance: float = 0.05, **kwargs) -> int:
        """
        Create/save a media file.

        For RealFiles, this just creates an empty file (media computation
        doesn't apply to real files being created).

        Args:
            name: Filename (required).
            extension: Optional explicit extension.
            tolerance: Ignored for RealFiles.
            **kwargs: File parameters.

        Returns:
            int: Always returns 0

        Raises:
            PermissionError: If allow_modifications is False
        """
        return self.save(name, extension, **kwargs)

    # =========================================================================
    # File Query Operations
    # =========================================================================

    def exists(self, path: str) -> bool:
        """Check if a file or directory exists."""
        abs_path = self._normalize_path(path)
        return os.path.exists(abs_path)

    def get_file(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Get file record by path.

        Returns file information in the same format as MockFiles.

        Args:
            path: Path to the file

        Returns:
            dict: Dictionary of file fields, or None if not found
        """
        abs_path = self._normalize_path(path)
        if not os.path.isfile(abs_path):
            return None
        return self._get_file_info(abs_path)

    def _get_file_info(self, path: str) -> Dict[str, Any]:
        """
        Get file information in MockFiles-compatible format.

        Args:
            path: Absolute path to the file

        Returns:
            dict: File information dictionary
        """
        stat = os.stat(path)
        p = Path(path)

        # Parse name and extension
        if '.' in p.name and not p.name.startswith('.'):
            name = p.stem
            extension = p.suffix[1:].lower() if p.suffix else ''
        elif p.name.startswith('.') and '.' in p.name[1:]:
            parts = p.name.rsplit('.', 1)
            name = parts[0]
            extension = parts[1].lower()
        else:
            name = p.name
            extension = ''

        # Check read-only (Windows: check file attributes, Unix: check write permission)
        try:
            readonly = not os.access(path, os.W_OK)
        except:
            readonly = False

        return {
            'name': name,
            'extension': extension,
            'size_bytes': stat.st_size,
            'mtime_ns': int(stat.st_mtime * 1e9),
            'ctime_ns': int(stat.st_ctime * 1e9),
            'size_on_disk': stat.st_size,  # Approximation
            'readonly': 1 if readonly else 0,
            'system': 0,  # Not easily detectable cross-platform
            'is_symlink': 1 if os.path.islink(path) else 0,
            'presence_state': 0,  # PRESENT
        }

    def find(self, pattern: str, path: str = None, recursive: bool = True) -> List[str]:
        """
        Find files matching fnmatch pattern.

        Args:
            pattern: fnmatch pattern (e.g., "*.txt")
            path: Directory to search in (defaults to cwd)
            recursive: If True, search subdirectories

        Returns:
            List of matching absolute paths
        """
        if path is None:
            search_path = self.cwd
        else:
            search_path = self._normalize_path(path)

        matches = []

        if recursive:
            for root, dirs, files in os.walk(search_path):
                for filename in files:
                    if fnmatch.fnmatch(filename, pattern):
                        matches.append(os.path.join(root, filename))
        else:
            try:
                for entry in os.scandir(search_path):
                    if entry.is_file() and fnmatch.fnmatch(entry.name, pattern):
                        matches.append(entry.path)
            except PermissionError:
                pass

        return sorted(matches)

    # =========================================================================
    # File Modification Operations
    # =========================================================================

    def delete(self, path: str) -> bool:
        """
        Delete a file.

        Args:
            path: Path to the file

        Returns:
            bool: True if deleted, False if not found

        Raises:
            PermissionError: If allow_modifications is False
        """
        self._check_modifications_allowed()
        abs_path = self._normalize_path(path)

        if not os.path.isfile(abs_path):
            return False

        os.remove(abs_path)  # <------- FILE OPERATION: delete file
        return True

    def set_attributes(self, path: str, **kwargs) -> bool:
        """
        Modify attributes of an existing file.

        For RealFiles, only limited attributes can be modified:
        - readonly: Sets/clears read-only flag
        - mtime: Sets modification time

        Args:
            path: Path to the file
            **kwargs: Attributes to modify

        Returns:
            bool: True if updated, False if file not found

        Raises:
            PermissionError: If allow_modifications is False
        """
        self._check_modifications_allowed()
        abs_path = self._normalize_path(path)

        if not os.path.isfile(abs_path):
            return False

        if 'readonly' in kwargs:
            import stat
            current = os.stat(abs_path).st_mode
            if kwargs['readonly']:
                os.chmod(abs_path, current & ~stat.S_IWRITE)  # <------- FILE OPERATION: chmod
            else:
                os.chmod(abs_path, current | stat.S_IWRITE)

        if 'mtime' in kwargs:
            mtime = kwargs['mtime']
            if isinstance(mtime, int):
                # Assume nanoseconds, convert to seconds
                mtime_sec = mtime / 1e9
            else:
                mtime_sec = mtime
            os.utime(abs_path, (os.stat(abs_path).st_atime, mtime_sec))  # <------- FILE OPERATION: utime

        return True

    def copy(self, source: str, dest: str, preserve_timestamps: bool = True) -> int:
        """
        Copy file(s) to destination.

        Args:
            source: Source file path or pattern with wildcards
            dest: Destination path (file or directory)
            preserve_timestamps: If True, preserve mtime/ctime

        Returns:
            int: Count of files copied

        Raises:
            PermissionError: If allow_modifications is False
        """
        self._check_modifications_allowed()

        # Expand wildcards
        source_files = self._expand_wildcards(source)

        if not source_files:
            return 0

        dest_abs = self._normalize_path(dest)
        dest_is_dir = os.path.isdir(dest_abs)

        if len(source_files) > 1 and not dest_is_dir:
            raise ValueError("Destination must be a directory when copying multiple files")

        count = 0
        for src_path in source_files:
            if dest_is_dir:
                dest_path = os.path.join(dest_abs, os.path.basename(src_path))
            else:
                dest_path = dest_abs

            if preserve_timestamps:
                shutil.copy2(src_path, dest_path)  # <------- FILE OPERATION: copy with metadata
            else:
                shutil.copy(src_path, dest_path)  # <------- FILE OPERATION: copy
            count += 1

        return count

    def move(self, source: str, dest: str) -> int:
        """
        Move/rename file(s).

        Args:
            source: Source file path or pattern with wildcards
            dest: Destination path (file or directory)

        Returns:
            int: Count of files moved

        Raises:
            PermissionError: If allow_modifications is False
        """
        self._check_modifications_allowed()

        source_files = self._expand_wildcards(source)

        if not source_files:
            return 0

        dest_abs = self._normalize_path(dest)
        dest_is_dir = os.path.isdir(dest_abs)

        if len(source_files) > 1 and not dest_is_dir:
            raise ValueError("Destination must be a directory when moving multiple files")

        count = 0
        for src_path in source_files:
            if dest_is_dir:
                dest_path = os.path.join(dest_abs, os.path.basename(src_path))
            else:
                dest_path = dest_abs

            shutil.move(src_path, dest_path)  # <------- FILE OPERATION: move file
            count += 1

        return count

    def _expand_wildcards(self, pattern: str) -> List[str]:
        """
        Expand wildcards in a file pattern.

        Args:
            pattern: Pattern with wildcards (e.g., "*.txt")

        Returns:
            List of matching absolute paths
        """
        abs_pattern = self._normalize_path(pattern)
        dir_part = os.path.dirname(abs_pattern)
        file_pattern = os.path.basename(abs_pattern)

        # If no wildcards, just return the path if it exists
        if '*' not in file_pattern and '?' not in file_pattern and '[' not in file_pattern:
            if os.path.isfile(abs_pattern):
                return [abs_pattern]
            return []

        # Expand wildcards
        matches = []
        if os.path.isdir(dir_part):
            try:
                for entry in os.scandir(dir_part):
                    if entry.is_file() and fnmatch.fnmatch(entry.name, file_pattern):
                        matches.append(entry.path)
            except PermissionError:
                pass

        return matches

    # =========================================================================
    # Permission Check Operations
    # =========================================================================

    def can_change(self, path: str) -> bool:
        """
        Check if a file can be modified.

        For RealFiles, this checks:
        - File exists
        - File is not read-only
        - allow_modifications flag is True

        Args:
            path: Full path to the file to check

        Returns:
            bool: True if the file exists and can be modified, False otherwise
        """
        abs_path = self._normalize_path(path)

        # Check existence
        if not os.path.isfile(abs_path):
            return False

        # Check allow_modifications flag
        if not self.allow_modifications:
            return False

        # Check write permission
        if not os.access(abs_path, os.W_OK):
            return False

        return True