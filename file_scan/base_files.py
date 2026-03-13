# base_files.py
"""
Abstract base class for file system implementations.

This module defines the BaseFiles interface that both MockFiles (virtual filesystem)
and RealFiles (actual filesystem) inherit from. This allows code to be written
against the base class and work with either implementation.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseFiles(ABC):
    """
    Abstract base class for file system implementations.

    Provides a common interface for both mock (virtual) and real file systems.
    All file system implementations should inherit from this class.
    """

    # =========================================================================
    # Time Operations
    # =========================================================================

    @abstractmethod
    def get_time(self) -> int:
        """
        Get current time in nanoseconds since epoch.

        For MockFiles: returns the mock clock time.
        For RealFiles: returns actual system time.

        Returns:
            int: Time in nanoseconds since epoch
        """
        pass

    @abstractmethod
    def set_time(self, time_value) -> None:
        """
        Set the current time.

        For MockFiles: sets the mock clock.
        For RealFiles: no-op (cannot set system time).

        Args:
            time_value: Nanoseconds (int) or parseable time string/datetime object.
        """
        pass

    @abstractmethod
    def increment_time(self, nanoseconds: int) -> None:
        """
        Advance time by the given number of nanoseconds.

        For MockFiles: advances the mock clock.
        For RealFiles: no-op (time advances naturally).

        Args:
            nanoseconds: Number of nanoseconds to advance.
        """
        pass

    # =========================================================================
    # Volume/Mount Operations
    # =========================================================================

    @abstractmethod
    def mount_volume(self, drive_letter=None, label=None, filesystem=None, serial_number=None) -> int:
        """
        Add/mount a new volume to the file system.

        For MockFiles: creates a virtual volume.
        For RealFiles: returns info about existing volume (read-only operation).

        Args:
            drive_letter: Drive letter (e.g., 'C', 'D').
            label: Human-readable volume label.
            filesystem: Filesystem type (e.g., "NTFS").
            serial_number: Hex serial number string.

        Returns:
            int: The volume ID
        """
        pass

    # =========================================================================
    # Working Directory Operations
    # =========================================================================

    @abstractmethod
    def getcwd(self) -> str:
        """
        Get the current working directory.

        Returns:
            str: The current working directory path
        """
        pass

    @abstractmethod
    def cd(self, path: str) -> None:
        """
        Change the current working directory.

        Args:
            path: Path to change to (can be relative or absolute)

        Raises:
            ValueError: If directory doesn't exist
        """
        pass

    # =========================================================================
    # Directory Operations
    # =========================================================================

    @abstractmethod
    def mkdir(self, path: str, parents: bool = True) -> None:
        """
        Create a directory (and optionally parent directories).

        Args:
            path: Path to create (can be relative or absolute)
            parents: If True, create parent directories as needed

        Raises:
            ValueError: If parents=False and parent doesn't exist
        """
        pass

    @abstractmethod
    def rmdir(self, path: str) -> None:
        """
        Remove a directory.

        Args:
            path: Path to remove (can be relative or absolute)

        Raises:
            ValueError: If directory doesn't exist or is not empty
        """
        pass

    @abstractmethod
    def ls(self) -> List[Dict[str, Any]]:
        """
        List all files in the current working directory.

        Returns:
            list: List of dictionaries containing file information
        """
        pass

    @abstractmethod
    def ls_dir(self) -> List[str]:
        """
        List all immediate subdirectories in the current working directory.

        Returns:
            list: List of subdirectory names
        """
        pass

    @abstractmethod
    def dir(self, path: str = None) -> str:
        """
        List all files and subdirectories in the given directory.

        Args:
            path: Directory to list (defaults to cwd)

        Returns:
            str: Formatted multi-line string of directory contents
        """
        pass

    @abstractmethod
    def copydir(self, source: str, dest: str) -> int:
        """
        Copy directory recursively.

        Args:
            source: Source directory path
            dest: Destination directory path

        Returns:
            int: Count of files copied
        """
        pass

    @abstractmethod
    def movedir(self, source: str, dest: str) -> int:
        """
        Move/rename directory.

        Args:
            source: Source directory path
            dest: Destination directory path

        Returns:
            int: Count of directories/files affected
        """
        pass

    # =========================================================================
    # File Defaults (for creating files)
    # =========================================================================

    @abstractmethod
    def set_file_defaults(self, **kwargs) -> None:
        """
        Set default values for file parameters when creating files.

        For MockFiles: sets defaults for save() operations.
        For RealFiles: may be no-op or limited functionality.

        Args:
            **kwargs: Parameter names and their default values.
        """
        pass

    @abstractmethod
    def get_file_defaults(self) -> Dict[str, Any]:
        """
        Get a copy of the current file defaults.

        Returns:
            dict: Copy of the defaults dictionary
        """
        pass

    # =========================================================================
    # File Creation Operations
    # =========================================================================

    @abstractmethod
    def save(self, name: str, extension: Optional[str] = None, **kwargs) -> int:
        """
        Create/save a file in the current working directory.

        Args:
            name: Filename (required). Can include extension or not.
            extension: Optional explicit extension.
            **kwargs: Other file parameters

        Returns:
            int: The file ID from the database/system
        """
        pass

    @abstractmethod
    def save_m(self, name: str, extension: Optional[str] = None,
               tolerance: float = 0.05, **kwargs) -> int:
        """
        Create/save a media file with automatic attribute computation.

        Args:
            name: Filename (required). Can include extension or not.
            extension: Optional explicit extension.
            tolerance: Allowed relative difference for conflict detection.
            **kwargs: Media parameters

        Returns:
            int: The file ID from the database/system
        """
        pass

    # =========================================================================
    # File Query Operations
    # =========================================================================

    @abstractmethod
    def exists(self, path: str) -> bool:
        """
        Check if a file or directory exists.

        Args:
            path: Path to check (can be relative or absolute)

        Returns:
            bool: True if file or directory exists
        """
        pass

    @abstractmethod
    def get_file(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Get file record by path.

        Args:
            path: Path to the file (can be relative or absolute)

        Returns:
            dict: Dictionary of file fields, or None if not found
        """
        pass

    @abstractmethod
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
        pass

    # =========================================================================
    # File Modification Operations
    # =========================================================================

    @abstractmethod
    def delete(self, path: str) -> bool:
        """
        Delete a file.

        Args:
            path: Path to the file (can be relative or absolute)

        Returns:
            bool: True if deleted, False if not found
        """
        pass

    # Alias for delete
    def rm(self, path: str) -> bool:
        """Alias for delete()."""
        return self.delete(path)

    @abstractmethod
    def set_attributes(self, path: str, **kwargs) -> bool:
        """
        Modify attributes of an existing file.

        Args:
            path: Path to the file (can be relative or absolute)
            **kwargs: Attributes to modify

        Returns:
            bool: True if updated, False if file not found
        """
        pass

    @abstractmethod
    def copy(self, source: str, dest: str, preserve_timestamps: bool = True) -> int:
        """
        Copy file(s) to destination.

        Args:
            source: Source file path or pattern with wildcards
            dest: Destination path (file or directory)
            preserve_timestamps: If True, preserve mtime/ctime

        Returns:
            int: Count of files copied
        """
        pass

    @abstractmethod
    def move(self, source: str, dest: str) -> int:
        """
        Move/rename file(s).

        Args:
            source: Source file path or pattern with wildcards
            dest: Destination path (file or directory)

        Returns:
            int: Count of files moved
        """
        pass

    # =========================================================================
    # Permission Check Operations
    # =========================================================================

    @abstractmethod
    def can_change(self, path: str) -> bool:
        """
        Check if a file can be modified.

        This checks various permission restrictions:
        - File existence
        - Read-only attribute on the file
        - Implementation-specific restrictions (e.g., RealFiles.allow_modifications flag)
        - SafeFiles path_guard restrictions (when wrapped)

        Args:
            path: Full path to the file to check

        Returns:
            bool: True if the file exists and can be modified, False otherwise
        """
        pass