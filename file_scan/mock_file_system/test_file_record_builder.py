# test_file_record_builder.py
"""Tests for the FileRecordBuilder class."""

import unittest
from datetime import datetime, date, time
from .file_record_builder import FileRecordBuilder


class TestFileRecordBuilderInit(unittest.TestCase):
    """Test FileRecordBuilder initialization."""

    def test_default_values_initialized(self):
        """Test that defaults are initialized correctly."""
        builder = FileRecordBuilder()
        defaults = builder.get_defaults()

        self.assertEqual(defaults['extension'], '')
        self.assertEqual(defaults['size_bytes'], 0)
        self.assertIsNone(defaults['mtime'])
        self.assertIsNone(defaults['ctime'])
        self.assertEqual(defaults['readonly'], 0)
        self.assertEqual(defaults['system'], 0)
        self.assertEqual(defaults['is_symlink'], 0)
        self.assertEqual(defaults['presence_state'], 0)

    def test_default_date_time_initialized(self):
        """Test that default date and time are set."""
        builder = FileRecordBuilder()

        # Using 2000-01-01 instead of epoch to avoid Windows timestamp issues
        self.assertEqual(builder.default_date, "2000-01-01")
        self.assertEqual(builder.default_time, "00:00:00")


class TestSetDefaults(unittest.TestCase):
    """Test the set_defaults method."""

    def test_set_single_default(self):
        """Test setting a single default value."""
        builder = FileRecordBuilder()
        builder.set_defaults(size_bytes=1024)

        self.assertEqual(builder.get_defaults()['size_bytes'], 1024)

    def test_set_multiple_defaults(self):
        """Test setting multiple default values at once."""
        builder = FileRecordBuilder()
        builder.set_defaults(
            size_bytes=2048,
            extension='txt',
            readonly=1
        )

        defaults = builder.get_defaults()
        self.assertEqual(defaults['size_bytes'], 2048)
        self.assertEqual(defaults['extension'], 'txt')
        self.assertEqual(defaults['readonly'], 1)

    def test_set_default_date(self):
        """Test setting the default date."""
        builder = FileRecordBuilder()
        builder.set_defaults(default_date="2024-01-15")

        self.assertEqual(builder.default_date, "2024-01-15")

    def test_set_default_time(self):
        """Test setting the default time."""
        builder = FileRecordBuilder()
        builder.set_defaults(default_time="10:30:00")

        self.assertEqual(builder.default_time, "10:30:00")

    def test_set_media_defaults(self):
        """Test setting media-related defaults."""
        builder = FileRecordBuilder()
        builder.set_defaults(
            duration=180.5,
            bitrate=320000,
            codec='aac',
            sample_rate=44100,
            channels=2
        )

        defaults = builder.get_defaults()
        self.assertEqual(defaults['duration'], 180.5)
        self.assertEqual(defaults['bitrate'], 320000)
        self.assertEqual(defaults['codec'], 'aac')
        self.assertEqual(defaults['sample_rate'], 44100)
        self.assertEqual(defaults['channels'], 2)

    def test_set_tag_defaults(self):
        """Test setting tag-related defaults."""
        builder = FileRecordBuilder()
        builder.set_defaults(
            tag_title='My Song',
            tag_artist='Some Artist',
            tag_album='Great Album'
        )

        defaults = builder.get_defaults()
        self.assertEqual(defaults['tag_title'], 'My Song')
        self.assertEqual(defaults['tag_artist'], 'Some Artist')
        self.assertEqual(defaults['tag_album'], 'Great Album')

    def test_set_unknown_parameter_raises(self):
        """Test that setting an unknown parameter raises ValueError."""
        builder = FileRecordBuilder()

        with self.assertRaises(ValueError) as context:
            builder.set_defaults(unknown_param=123)

        self.assertIn("Unknown parameter", str(context.exception))


class TestParseFilename(unittest.TestCase):
    """Test the parse_filename method."""

    def test_filename_with_extension(self):
        """Test parsing a filename that has an extension."""
        builder = FileRecordBuilder()
        name, ext = builder.parse_filename("document.txt")

        self.assertEqual(name, "document")
        self.assertEqual(ext, "txt")

    def test_filename_without_extension_uses_default(self):
        """Test that filename without extension uses the default."""
        builder = FileRecordBuilder()
        builder.set_defaults(extension='pdf')
        name, ext = builder.parse_filename("myfile")

        self.assertEqual(name, "myfile")
        self.assertEqual(ext, "pdf")

    def test_filename_without_extension_empty_default(self):
        """Test filename without extension when default is empty."""
        builder = FileRecordBuilder()
        name, ext = builder.parse_filename("myfile")

        self.assertEqual(name, "myfile")
        self.assertEqual(ext, "")

    def test_explicit_extension_parameter(self):
        """Test providing explicit extension parameter."""
        builder = FileRecordBuilder()
        name, ext = builder.parse_filename("myfile", extension='doc')

        self.assertEqual(name, "myfile")
        self.assertEqual(ext, "doc")

    def test_explicit_empty_extension(self):
        """Test explicitly setting extension to empty string."""
        builder = FileRecordBuilder()
        builder.set_defaults(extension='txt')  # Set a default
        name, ext = builder.parse_filename("myfile", extension='')

        self.assertEqual(name, "myfile")
        self.assertEqual(ext, "")

    def test_extension_normalized_to_lowercase(self):
        """Test that extensions are normalized to lowercase."""
        builder = FileRecordBuilder()
        name, ext = builder.parse_filename("document.TXT")

        self.assertEqual(ext, "txt")

    def test_explicit_extension_normalized(self):
        """Test that explicit extension is normalized to lowercase."""
        builder = FileRecordBuilder()
        name, ext = builder.parse_filename("myfile", extension='PDF')

        self.assertEqual(ext, "pdf")

    def test_error_when_both_extension_in_name_and_parameter(self):
        """Test error when extension in name AND as parameter."""
        builder = FileRecordBuilder()

        with self.assertRaises(ValueError) as context:
            builder.parse_filename("document.txt", extension='pdf')

        self.assertIn("Cannot specify both", str(context.exception))

    def test_multiple_dots_uses_last_extension(self):
        """Test that multiple dots correctly parse last as extension."""
        builder = FileRecordBuilder()
        name, ext = builder.parse_filename("my.file.name.txt")

        self.assertEqual(name, "my.file.name")
        self.assertEqual(ext, "txt")

    def test_hidden_file_no_extension(self):
        """Test that files starting with dot are handled correctly."""
        builder = FileRecordBuilder()
        builder.set_defaults(extension='cfg')
        name, ext = builder.parse_filename(".gitignore")

        # .gitignore should be treated as having no extension in name
        self.assertEqual(name, ".gitignore")
        self.assertEqual(ext, "cfg")  # Uses default

    def test_hidden_file_with_extension(self):
        """Test hidden file with an extension."""
        builder = FileRecordBuilder()
        name, ext = builder.parse_filename(".config.json")

        self.assertEqual(name, ".config")
        self.assertEqual(ext, "json")


class TestParseTime(unittest.TestCase):
    """Test the parse_time method."""

    def test_none_returns_none(self):
        """Test that None input returns None."""
        builder = FileRecordBuilder()
        result = builder.parse_time(None)

        self.assertIsNone(result)

    def test_int_returned_as_is(self):
        """Test that integer input (nanoseconds) is returned as-is."""
        builder = FileRecordBuilder()
        ns = 1705320000000000000
        result = builder.parse_time(ns)

        self.assertEqual(result, ns)

    def test_datetime_object(self):
        """Test parsing a datetime object."""
        builder = FileRecordBuilder()
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = builder.parse_time(dt)

        # Should be nanoseconds since epoch
        expected_ns = int(dt.timestamp() * 1_000_000_000)
        self.assertEqual(result, expected_ns)

    def test_date_object_uses_default_time(self):
        """Test that date object uses default time."""
        builder = FileRecordBuilder()
        builder.set_defaults(default_time="12:00:00")
        d = date(2024, 1, 15)
        result = builder.parse_time(d)

        expected_dt = datetime(2024, 1, 15, 12, 0, 0)
        expected_ns = int(expected_dt.timestamp() * 1_000_000_000)
        self.assertEqual(result, expected_ns)

    def test_time_object_uses_default_date(self):
        """Test that time object uses default date."""
        builder = FileRecordBuilder()
        builder.set_defaults(default_date="2024-06-01")
        t = time(10, 30, 0)
        result = builder.parse_time(t)

        expected_dt = datetime(2024, 6, 1, 10, 30, 0)
        expected_ns = int(expected_dt.timestamp() * 1_000_000_000)
        self.assertEqual(result, expected_ns)

    def test_iso_datetime_string_space(self):
        """Test parsing ISO datetime string with space separator."""
        builder = FileRecordBuilder()
        result = builder.parse_time("2024-01-15 10:30:00")

        expected_dt = datetime(2024, 1, 15, 10, 30, 0)
        expected_ns = int(expected_dt.timestamp() * 1_000_000_000)
        self.assertEqual(result, expected_ns)

    def test_iso_datetime_string_t_separator(self):
        """Test parsing ISO datetime string with T separator."""
        builder = FileRecordBuilder()
        result = builder.parse_time("2024-01-15T10:30:00")

        expected_dt = datetime(2024, 1, 15, 10, 30, 0)
        expected_ns = int(expected_dt.timestamp() * 1_000_000_000)
        self.assertEqual(result, expected_ns)

    def test_date_only_string(self):
        """Test parsing date-only string uses default time."""
        builder = FileRecordBuilder()
        builder.set_defaults(default_time="08:00:00")
        result = builder.parse_time("2024-01-15")

        expected_dt = datetime(2024, 1, 15, 8, 0, 0)
        expected_ns = int(expected_dt.timestamp() * 1_000_000_000)
        self.assertEqual(result, expected_ns)

    def test_time_only_string(self):
        """Test parsing time-only string uses default date."""
        builder = FileRecordBuilder()
        builder.set_defaults(default_date="2024-06-01")
        result = builder.parse_time("14:30:00")

        expected_dt = datetime(2024, 6, 1, 14, 30, 0)
        expected_ns = int(expected_dt.timestamp() * 1_000_000_000)
        self.assertEqual(result, expected_ns)

    def test_time_only_string_short_format(self):
        """Test parsing time-only string without seconds."""
        builder = FileRecordBuilder()
        builder.set_defaults(default_date="2024-06-01")
        result = builder.parse_time("14:30")

        expected_dt = datetime(2024, 6, 1, 14, 30, 0)
        expected_ns = int(expected_dt.timestamp() * 1_000_000_000)
        self.assertEqual(result, expected_ns)

    def test_invalid_string_raises(self):
        """Test that invalid time string raises ValueError."""
        builder = FileRecordBuilder()

        with self.assertRaises(ValueError):
            builder.parse_time("not a time")

    def test_default_date_used_for_time_only(self):
        """Test that default date (2000-01-01) is used when only time is given."""
        builder = FileRecordBuilder()
        result = builder.parse_time("12:00:00")

        # Default date is 2000-01-01 to avoid Windows timestamp issues
        expected_dt = datetime(2000, 1, 1, 12, 0, 0)
        expected_ns = int(expected_dt.timestamp() * 1_000_000_000)
        self.assertEqual(result, expected_ns)


class TestBuildRecord(unittest.TestCase):
    """Test the build_record method."""

    def test_basic_record(self):
        """Test building a basic file record."""
        builder = FileRecordBuilder()
        record = builder.build_record("document.txt")

        self.assertEqual(record['name'], "document")
        self.assertEqual(record['extension'], "txt")
        self.assertEqual(record['size_bytes'], 0)

    def test_record_uses_defaults(self):
        """Test that record uses set defaults."""
        builder = FileRecordBuilder()
        builder.set_defaults(size_bytes=1024, readonly=1)
        record = builder.build_record("myfile.pdf")

        self.assertEqual(record['size_bytes'], 1024)
        self.assertEqual(record['readonly'], 1)

    def test_provided_params_override_defaults(self):
        """Test that provided parameters override defaults."""
        builder = FileRecordBuilder()
        builder.set_defaults(size_bytes=1024)
        record = builder.build_record("myfile.txt", size_bytes=2048)

        self.assertEqual(record['size_bytes'], 2048)

    def test_provided_params_update_defaults(self):
        """Test that provided parameters update defaults for future use."""
        builder = FileRecordBuilder()
        builder.set_defaults(size_bytes=1024)

        # First record with explicit size
        record1 = builder.build_record("file1.txt", size_bytes=2048)

        # Second record should use updated default
        record2 = builder.build_record("file2.txt")

        self.assertEqual(record1['size_bytes'], 2048)
        self.assertEqual(record2['size_bytes'], 2048)

    def test_extension_from_name_updates_default(self):
        """Test that extension from filename updates the default."""
        builder = FileRecordBuilder()

        record1 = builder.build_record("document.pdf")
        record2 = builder.build_record("another")  # Should use pdf as default

        self.assertEqual(record1['extension'], "pdf")
        self.assertEqual(record2['extension'], "pdf")

    def test_explicit_extension_updates_default(self):
        """Test that explicit extension parameter updates the default."""
        builder = FileRecordBuilder()

        record1 = builder.build_record("myfile", extension='doc')
        record2 = builder.build_record("another")

        self.assertEqual(record1['extension'], "doc")
        self.assertEqual(record2['extension'], "doc")

    def test_explicit_empty_extension_updates_default(self):
        """Test that explicit empty extension updates the default."""
        builder = FileRecordBuilder()
        builder.set_defaults(extension='txt')

        record1 = builder.build_record("myfile", extension='')
        record2 = builder.build_record("another")

        self.assertEqual(record1['extension'], "")
        self.assertEqual(record2['extension'], "")

    def test_time_converted_to_nanoseconds(self):
        """Test that mtime and ctime are converted to nanoseconds."""
        builder = FileRecordBuilder()
        record = builder.build_record(
            "myfile.txt",
            mtime="2024-01-15 10:30:00",
            ctime="2024-01-15 08:00:00"
        )

        self.assertIn('mtime_ns', record)
        self.assertIn('ctime_ns', record)
        self.assertIsInstance(record['mtime_ns'], int)
        self.assertIsInstance(record['ctime_ns'], int)

    def test_unknown_parameter_raises(self):
        """Test that unknown parameter raises ValueError."""
        builder = FileRecordBuilder()

        with self.assertRaises(ValueError) as context:
            builder.build_record("myfile.txt", unknown_param=123)

        self.assertIn("Unknown parameter", str(context.exception))

    def test_all_media_fields_in_record(self):
        """Test that all media fields are included in record."""
        builder = FileRecordBuilder()
        builder.set_defaults(
            duration=180.5,
            bitrate=320000,
            codec='aac',
            framerate=30.0,
            image_format='mp4',
            resolution_width=1920,
            resolution_height=1080,
            sample_rate=44100,
            channels=2
        )
        record = builder.build_record("video.mp4")

        self.assertEqual(record['duration'], 180.5)
        self.assertEqual(record['bitrate'], 320000)
        self.assertEqual(record['codec'], 'aac')
        self.assertEqual(record['framerate'], 30.0)
        self.assertEqual(record['image_format'], 'mp4')
        self.assertEqual(record['resolution_width'], 1920)
        self.assertEqual(record['resolution_height'], 1080)
        self.assertEqual(record['sample_rate'], 44100)
        self.assertEqual(record['channels'], 2)

    def test_all_tag_fields_in_record(self):
        """Test that all tag fields are included in record."""
        builder = FileRecordBuilder()
        builder.set_defaults(
            tag_title='My Song',
            tag_artist='Artist Name',
            tag_album='Album Title',
            tag_album_artist='Various Artists',
            tag_track='5',
            tag_date='2024'
        )
        record = builder.build_record("song.mp3")

        self.assertEqual(record['tag_title'], 'My Song')
        self.assertEqual(record['tag_artist'], 'Artist Name')
        self.assertEqual(record['tag_album'], 'Album Title')
        self.assertEqual(record['tag_album_artist'], 'Various Artists')
        self.assertEqual(record['tag_track'], '5')
        self.assertEqual(record['tag_date'], '2024')

    def test_record_has_all_expected_fields(self):
        """Test that record contains all expected fields."""
        builder = FileRecordBuilder()
        record = builder.build_record("test.txt")

        expected_fields = [
            'name', 'extension', 'size_bytes', 'mtime_ns', 'ctime_ns',
            'size_on_disk', 'readonly', 'system', 'is_symlink', 'presence_state',
            'duration', 'bitrate', 'codec', 'framerate', 'image_format',
            'resolution_width', 'resolution_height', 'sample_rate', 'channels',
            'tag_title', 'tag_artist', 'tag_album', 'tag_album_artist',
            'tag_track', 'tag_date'
        ]

        for field in expected_fields:
            self.assertIn(field, record, f"Missing field: {field}")


if __name__ == '__main__':
    unittest.main()