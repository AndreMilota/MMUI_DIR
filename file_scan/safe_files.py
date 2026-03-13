# safe_files.py
"""
SafeFiles: A wrapper that adds path-based permission checking to any BaseFiles implementation.

This module provides SafeFiles, which wraps any BaseFiles (MockFiles, RealFiles, etc.)
and uses PathGuard to check permissions before allowing modification operations.

Usage:
    from file_scan.mock_file_system.mock_files import MockFiles
    from file_scan.path_guard import PathGuard
    from file_scan.safe_files import SafeFiles

    # Create base filesystem
    fs = MockFiles(":memory:")
    fs.mount_volume("C")

    # Create guard with rules
    guard = PathGuard()
    guard.allow("DISK001", "C:/allowed/**")
    guard.deny("DISK001", "C:/allowed/forbidden/**")

    # Wrap with SafeFiles
    safe_fs = SafeFiles(fs, guard, disk_id="DISK001")

    # Now modifications are checked against guard rules
    safe_fs.cd("C:/allowed")
    safe_fs.save("file.txt")  # OK - allowed path

    safe_fs.cd("C:/allowed/forbidden")
    safe_fs.save("file.txt")  # Raises PermissionError - denied path
"""
from typing import List, Dict, Any, Optional, Union, Callable
from .base_files import BaseFiles
from .path_guard import PathGuard


class SafeFiles(BaseFiles):
    """
    A wrapper that adds path-based permission checking to any BaseFiles implementation.

    SafeFiles uses composition to wrap any BaseFiles instance. All read operations
    are delegated directly. Modification operations are checked against a PathGuard
    before being allowed.

    Modification operations that are checked:
    - mkdir, rmdir
    - save, save_m
    - delete/rm
    - set_attributes
    - copy, move (destination is checked)
    - copydir, movedir (destination is checked)

    Read operations that are NOT checked:
    - getcwd, cd (cd is not a filesystem modification)
    - ls, ls_dir, dir
    - exists, get_file, find
    - get_time, set_time, increment_time
    - mount_volume (for MockFiles, this is setup not file modification)
    - get_file_defaults, set_file_defaults
    """

    def __init__(
        self,
        fs: BaseFiles,
        guard: PathGuard,
        disk_id: Union[str, Callable[[str], str]]
    ):
        """
        Initialize SafeFiles wrapper.

        Args:
            fs: The BaseFiles instance to wrap (MockFiles, RealFiles, etc.)
            guard: PathGuard instance with permission rules
            disk_id: Either a string disk ID that applies to all paths,
                     or a callable that takes a path and returns the disk_id
        """
        self._fs = fs
        self._guard = guard
        self._disk_id = disk_id

    def _get_disk_id(self, path: str) -> str:
        """Get the disk ID for a given path."""
        if callable(self._disk_id):
            return self._disk_id(path)
        return self._disk_id

    def _check_permission(self, path: str, operation: str) -> None:
        """
        Check if an operation is permitted on the given path.

        Args:
            path: Path to check
            operation: Description of the operation for error message

        Raises:
            PermissionError: If the operation is not permitted
        """
        disk_id = self._get_disk_id(path)
        if not self._guard.ok(disk_id, path):
            raise PermissionError(
                f"PathGuard denied {operation} on path: {path} (disk_id={disk_id})"
            )

    def _get_absolute_path(self, path: str) -> str:
        """Get the absolute path using the wrapped filesystem's normalization."""
        # For files, combine cwd with relative path
        if not self._is_absolute_path(path):
            return self._fs.getcwd() + '/' + path.replace('\\', '/')
        return path.replace('\\', '/')

    def _is_absolute_path(self, path: str) -> bool:
        """Check if a path is absolute (has drive letter on Windows)."""
        path = path.replace('\\', '/')
        # Windows absolute path: C:/ or similar
        if len(path) >= 2 and path[1] == ':':
            return True
        # Unix absolute path
        if path.startswith('/'):
            return True
        return False

    # =========================================================================
    # Time Operations (delegated, no permission check)
    # =========================================================================

    def get_time(self) -> int:
        return self._fs.get_time()

    def set_time(self, time_value) -> None:
        self._fs.set_time(time_value)

    def increment_time(self, nanoseconds: int) -> None:
        self._fs.increment_time(nanoseconds)

    # =========================================================================
    # Volume/Mount Operations (delegated, no permission check)
    # =========================================================================

    def mount_volume(self, drive_letter=None, label=None, filesystem=None, serial_number=None) -> int:
        return self._fs.mount_volume(drive_letter, label, filesystem, serial_number)

    # =========================================================================
    # Working Directory Operations (delegated, no permission check)
    # =========================================================================

    def getcwd(self) -> str:
        return self._fs.getcwd()

    def cd(self, path: str) -> None:
        self._fs.cd(path)

    # =========================================================================
    # Directory Operations (permission checked for modifications)
    # =========================================================================

    def mkdir(self, path: str, parents: bool = True) -> None:
        abs_path = self._get_absolute_path(path)
        self._check_permission(abs_path, "mkdir")
        self._fs.mkdir(path, parents)

    def rmdir(self, path: str) -> None:
        abs_path = self._get_absolute_path(path)
        self._check_permission(abs_path, "rmdir")
        self._fs.rmdir(path)

    def ls(self) -> List[Dict[str, Any]]:
        return self._fs.ls()

    def ls_dir(self) -> List[str]:
        return self._fs.ls_dir()

    def dir(self, path: str = None) -> str:
        return self._fs.dir(path)

    def copydir(self, source: str, dest: str) -> int:
        dest_abs = self._get_absolute_path(dest)
        self._check_permission(dest_abs, "copydir")
        return self._fs.copydir(source, dest)

    def movedir(self, source: str, dest: str) -> int:
        # Check both source (being removed) and dest (being created)
        source_abs = self._get_absolute_path(source)
        dest_abs = self._get_absolute_path(dest)
        self._check_permission(source_abs, "movedir (source)")
        self._check_permission(dest_abs, "movedir (dest)")
        return self._fs.movedir(source, dest)

    # =========================================================================
    # File Defaults (delegated, no permission check)
    # =========================================================================

    def set_file_defaults(self, **kwargs) -> None:
        self._fs.set_file_defaults(**kwargs)

    def get_file_defaults(self) -> Dict[str, Any]:
        return self._fs.get_file_defaults()

    # =========================================================================
    # File Creation Operations (permission checked)
    # =========================================================================

    def save(self, name: str, extension: Optional[str] = None, **kwargs) -> int:
        # Build full filename
        if extension is not None:
            filename = f"{name}.{extension}" if extension else name
        else:
            filename = name

        abs_path = self._get_absolute_path(filename)
        self._check_permission(abs_path, "save")
        return self._fs.save(name, extension, **kwargs)

    def save_m(self, name: str, extension: Optional[str] = None,
               tolerance: float = 0.05, **kwargs) -> int:
        if extension is not None:
            filename = f"{name}.{extension}" if extension else name
        else:
            filename = name

        abs_path = self._get_absolute_path(filename)
        self._check_permission(abs_path, "save_m")
        return self._fs.save_m(name, extension, tolerance, **kwargs)

    # =========================================================================
    # File Query Operations (delegated, no permission check)
    # =========================================================================

    def exists(self, path: str) -> bool:
        return self._fs.exists(path)

    def get_file(self, path: str) -> Optional[Dict[str, Any]]:
        return self._fs.get_file(path)

    def find(self, pattern: str, path: str = None, recursive: bool = True) -> List[str]:
        return self._fs.find(pattern, path, recursive)

    # =========================================================================
    # File Modification Operations (permission checked)
    # =========================================================================

    def delete(self, path: str) -> bool:
        abs_path = self._get_absolute_path(path)
        self._check_permission(abs_path, "delete")
        return self._fs.delete(path)

    def set_attributes(self, path: str, **kwargs) -> bool:
        abs_path = self._get_absolute_path(path)
        self._check_permission(abs_path, "set_attributes")
        return self._fs.set_attributes(path, **kwargs)

    def copy(self, source: str, dest: str, preserve_timestamps: bool = True) -> int:
        dest_abs = self._get_absolute_path(dest)
        self._check_permission(dest_abs, "copy")
        return self._fs.copy(source, dest, preserve_timestamps)

    def move(self, source: str, dest: str) -> int:
        # Check both source (being removed) and dest (being created)
        source_abs = self._get_absolute_path(source)
        dest_abs = self._get_absolute_path(dest)
        self._check_permission(source_abs, "move (source)")
        self._check_permission(dest_abs, "move (dest)")
        return self._fs.move(source, dest)

    # =========================================================================
    # Permission Check Operations
    # =========================================================================

    def can_change(self, path: str) -> bool:
        """
        Check if a file can be modified.

        For SafeFiles, this checks:
        - Underlying filesystem can_change (file exists, not read-only, etc.)
        - PathGuard allows the path

        Args:
            path: Full path to the file to check

        Returns:
            bool: True if the file can be modified, False otherwise
        """
        # First check underlying filesystem
        if not self._fs.can_change(path):
            return False

        # Then check PathGuard
        abs_path = self._get_absolute_path(path)
        disk_id = self._get_disk_id(abs_path)
        return self._guard.ok(disk_id, abs_path)

    # =========================================================================
    # Access to underlying filesystem and guard
    # =========================================================================

    @property
    def wrapped_fs(self) -> BaseFiles:
        """Get the wrapped BaseFiles instance."""
        return self._fs

    @property
    def guard(self) -> PathGuard:
        """Get the PathGuard instance."""
        return self._guard