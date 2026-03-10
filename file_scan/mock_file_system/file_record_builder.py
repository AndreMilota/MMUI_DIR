# file_record_builder.py
"""
FileRecordBuilder - Manages file parameter defaults and record construction for MockFiles.

This class handles:
- Default values for all file record fields (size, times, attributes, media tags, etc.)
- Time parsing (human-readable strings/datetime objects to nanoseconds)
- Filename parsing (splitting name and extension)
- Building complete file records with defaults applied

The class is designed to be used by MockFiles to construct file records for insertion
into the fs_database. When parameters are specified during record building, they both
get applied to the current record AND update the defaults for future records.

Usage:
    builder = FileRecordBuilder()
    builder.set_defaults(size_bytes=1024, extension='txt')
    record = builder.build_record('myfile.doc', size_bytes=2048)
    # record has size_bytes=2048, extension='doc'
    # defaults now have size_bytes=2048, extension='doc'
"""

from datetime import datetime, date, time
from typing import Optional, Dict, Any, Tuple, Union

# Sentinel value to distinguish "not provided" from "explicitly None or empty string"
_NOT_PROVIDED = object()


class FileRecordBuilder:
    """
    Builds file records with configurable defaults for MockFiles.

    All file parameters can have defaults set, and when building a record,
    any explicitly provided parameters will both be used for that record
    and update the defaults for future records.
    """

    # Default date/time for when only partial time info is provided
    # Using 2000-01-01 instead of epoch to avoid Windows timestamp issues
    # (Windows doesn't support timestamps before 1970 in some timezones)
    DEFAULT_DATE = "2000-01-01"
    DEFAULT_TIME = "00:00:00"

    # All valid file parameter names (excluding 'name' which is always required)
    VALID_PARAMS = frozenset([
        'extension',
        'size_bytes',
        'mtime',
        'ctime',
        'size_on_disk',
        'readonly',
        'system',
        'is_symlink',
        'presence_state',
        # Media fields
        'duration',
        'bitrate',
        'codec',
        'framerate',
        'image_format',
        'resolution_width',
        'resolution_height',
        'sample_rate',
        'channels',
        # Tag fields
        'tag_title',
        'tag_artist',
        'tag_album',
        'tag_album_artist',
        'tag_track',
        'tag_date',
    ])

    # Special parameters for date/time defaults
    DATETIME_PARAMS = frozenset(['default_date', 'default_time'])

    def __init__(self):
        """Initialize with default values for all file parameters."""
        # Default date and time for partial time specifications
        self._default_date = self.DEFAULT_DATE
        self._default_time = self.DEFAULT_TIME

        # File parameter defaults
        self._defaults: Dict[str, Any] = {
            'extension': '',
            'size_bytes': 0,
            'mtime': None,  # Will be converted to nanoseconds when building
            'ctime': None,
            'size_on_disk': None,
            'readonly': 0,
            'system': 0,
            'is_symlink': 0,
            'presence_state': 0,
            # Media fields
            'duration': None,
            'bitrate': None,
            'codec': None,
            'framerate': None,
            'image_format': None,
            'resolution_width': None,
            'resolution_height': None,
            'sample_rate': None,
            'channels': None,
            # Tag fields
            'tag_title': None,
            'tag_artist': None,
            'tag_album': None,
            'tag_album_artist': None,
            'tag_track': None,
            'tag_date': None,
        }

    @property
    def default_date(self) -> str:
        """Get the default date used when only time is provided."""
        return self._default_date

    @property
    def default_time(self) -> str:
        """Get the default time used when only date is provided."""
        return self._default_time

    def get_defaults(self) -> Dict[str, Any]:
        """
        Get a copy of the current defaults.

        Returns:
            dict: Copy of the defaults dictionary
        """
        return self._defaults.copy()

    def set_defaults(self, **kwargs) -> None:
        """
        Set default values for file parameters.

        Args:
            **kwargs: Parameter names and their default values.
                      Special parameters: default_date, default_time

        Raises:
            ValueError: If an unknown parameter name is provided
        """
        for key, value in kwargs.items():
            if key in self.VALID_PARAMS:
                self._defaults[key] = value
            elif key == 'default_date':
                self._default_date = value
            elif key == 'default_time':
                self._default_time = value
            else:
                raise ValueError(f"Unknown parameter: {key}")

    def parse_filename(
        self,
        name: str,
        extension: Any = _NOT_PROVIDED
    ) -> Tuple[str, str]:
        """
        Parse a filename into name and extension parts.

        Rules:
        - If name contains '.', split into name and extension
        - If extension parameter is also provided when name has extension, raise error
        - If name has no extension and extension not provided, use default
        - If extension is '' (empty string), file will have no extension
        - Extensions are normalized to lowercase

        Args:
            name: Filename (with or without extension)
            extension: Optional explicit extension. Use '' for no extension.
                      If not provided, uses default when name has no extension.

        Returns:
            tuple: (name_without_extension, extension)

        Raises:
            ValueError: If name contains extension AND extension parameter is also set
        """
        # Check if name has an extension
        # A file has an extension if there's a dot that's not at the start
        # For hidden files (starting with .), we check if there's another dot after the first char
        # Examples: "file.txt" -> has extension, ".gitignore" -> no extension, ".config.json" -> has extension
        if name.startswith('.'):
            # Hidden file - check for a dot after the first character
            has_extension_in_name = '.' in name[1:]
        else:
            # Regular file - just check for any dot
            has_extension_in_name = '.' in name

        if has_extension_in_name:
            # Split on last dot
            parts = name.rsplit('.', 1)
            name_part = parts[0]
            ext_from_name = parts[1].lower()

            if extension is not _NOT_PROVIDED:
                raise ValueError(
                    f"Cannot specify both extension in filename '{name}' "
                    f"and as parameter '{extension}'"
                )
            return name_part, ext_from_name
        else:
            # No extension in name
            if extension is not _NOT_PROVIDED:
                # Explicit extension provided (could be '' for no extension)
                return name, extension.lower() if extension else ''
            else:
                # Use default extension
                return name, self._defaults['extension']

    def parse_time(
        self,
        time_value: Union[str, datetime, date, time, int, None]
    ) -> Optional[int]:
        """
        Convert human-readable time to nanoseconds since epoch.

        Supports:
        - None: Returns None
        - int: Assumed to already be nanoseconds, returned as-is
        - datetime objects: Converted to nanoseconds
        - date objects: Combined with default_time, converted to nanoseconds
        - time objects: Combined with default_date, converted to nanoseconds
        - ISO format strings ("2024-01-15 10:30:00", "2024-01-15T10:30:00")
        - Date-only strings ("2024-01-15"): Uses default_time
        - Time-only strings ("10:30:00", "10:30"): Uses default_date

        Returns:
            int: Nanoseconds since epoch, or None if input is None

        Raises:
            ValueError: If the time string format cannot be parsed
        """
        if time_value is None:
            return None

        if isinstance(time_value, int):
            # Already nanoseconds
            return time_value

        if isinstance(time_value, datetime):
            return int(time_value.timestamp() * 1_000_000_000)

        if isinstance(time_value, date) and not isinstance(time_value, datetime):
            # date object (but not datetime) - combine with default time
            time_parts = self._parse_time_string(self._default_time)
            dt = datetime.combine(time_value, time_parts)
            return int(dt.timestamp() * 1_000_000_000)

        if isinstance(time_value, time):
            # time object - combine with default date
            date_parts = self._parse_date_string(self._default_date)
            dt = datetime.combine(date_parts, time_value)
            return int(dt.timestamp() * 1_000_000_000)

        if isinstance(time_value, str):
            return self._parse_time_string_to_ns(time_value)

        raise ValueError(f"Unsupported time value type: {type(time_value)}")

    def _parse_date_string(self, date_str: str) -> date:
        """Parse a date string into a date object."""
        # Try common date formats
        for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%d-%m-%Y'):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Cannot parse date string: {date_str}")

    def _parse_time_string(self, time_str: str) -> time:
        """Parse a time string into a time object."""
        # Try common time formats
        for fmt in ('%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p'):
            try:
                return datetime.strptime(time_str, fmt).time()
            except ValueError:
                continue
        raise ValueError(f"Cannot parse time string: {time_str}")

    def _parse_time_string_to_ns(self, time_str: str) -> int:
        """Parse a time/date/datetime string to nanoseconds."""
        time_str = time_str.strip()

        # Try full datetime formats first
        datetime_formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%dT%H:%M',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M',
        ]
        for fmt in datetime_formats:
            try:
                dt = datetime.strptime(time_str, fmt)
                return int(dt.timestamp() * 1_000_000_000)
            except ValueError:
                continue

        # Try date-only formats
        date_formats = ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%d-%m-%Y']
        for fmt in date_formats:
            try:
                d = datetime.strptime(time_str, fmt).date()
                t = self._parse_time_string(self._default_time)
                dt = datetime.combine(d, t)
                return int(dt.timestamp() * 1_000_000_000)
            except ValueError:
                continue

        # Try time-only formats
        time_formats = ['%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p']
        for fmt in time_formats:
            try:
                t = datetime.strptime(time_str, fmt).time()
                d = self._parse_date_string(self._default_date)
                dt = datetime.combine(d, t)
                return int(dt.timestamp() * 1_000_000_000)
            except ValueError:
                continue

        raise ValueError(f"Cannot parse time string: {time_str}")

    def build_record(
        self,
        name: str,
        extension: Any = _NOT_PROVIDED,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Build a complete file record dict with defaults applied.

        Specified parameters also update the defaults for future use.

        Args:
            name: Filename (required, with or without extension)
            extension: Optional explicit extension. Use '' for no extension.
            **kwargs: Other file parameters (size_bytes, mtime, ctime, etc.)

        Returns:
            dict: Complete file record ready for database insertion.
                  Contains 'name', 'extension', and all other file fields.

        Raises:
            ValueError: If name contains extension AND extension is also provided,
                       or if an unknown parameter is provided.
        """
        # Validate kwargs
        for key in kwargs:
            if key not in self.VALID_PARAMS and key not in self.DATETIME_PARAMS:
                if key != 'extension':  # extension handled separately
                    raise ValueError(f"Unknown parameter: {key}")

        # Parse filename
        parsed_name, parsed_extension = self.parse_filename(name, extension)

        # Update extension default if extension was explicitly provided or parsed from name
        if extension is not _NOT_PROVIDED:
            self._defaults['extension'] = parsed_extension
        elif name.startswith('.') and '.' in name[1:]:
            # Hidden file with extension (e.g., .config.json)
            self._defaults['extension'] = parsed_extension
        elif not name.startswith('.') and '.' in name:
            # Regular file with extension (e.g., file.txt)
            self._defaults['extension'] = parsed_extension

        # Update defaults with any provided kwargs (before building record)
        for key, value in kwargs.items():
            if key in self.VALID_PARAMS:
                self._defaults[key] = value
            elif key == 'default_date':
                self._default_date = value
            elif key == 'default_time':
                self._default_time = value

        # Build the record using current defaults
        record = {
            'name': parsed_name,
            'extension': parsed_extension,
        }

        # Add all other fields from defaults
        for key in self.VALID_PARAMS:
            if key == 'extension':
                continue  # Already handled

            value = self._defaults[key]

            # Convert time fields to nanoseconds
            if key in ('mtime', 'ctime') and value is not None:
                record[f'{key}_ns'] = self.parse_time(value)
            elif key in ('mtime', 'ctime'):
                record[f'{key}_ns'] = None
            else:
                record[key] = value

        return record