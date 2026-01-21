# this file is for testing the mock_files interface

import unittest
import tempfile
import os
from pathlib import Path
from .mock_files import MockFiles
from ..fs_database import FSDatabase


class TestMockFilesInit(unittest.TestCase):
    """Test the __init__ function of MockFiles class"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name

    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_init_with_c_drive_mounted(self):
        """Test that C drive is selected when it's mounted"""
        # Setup: Create a database with C drive mounted
        db = FSDatabase(self.db_path)
        db.upsert_volume(
            volume_key="1234ABCD-NTFS",
            root_path="C:\\",
            label="System",
            filesystem="NTFS",
            serial_number="1234ABCD"
        )
        db.upsert_volume(
            volume_key="5678EFGH-NTFS",
            root_path="D:\\",
            label="Data",
            filesystem="NTFS",
            serial_number="5678EFGH"
        )
        db.close()

        # Test: Create MockFiles and check cwd
        mock_fs = MockFiles(self.db_path)
        self.assertEqual(mock_fs.cwd, "C:\\")
        mock_fs.db.close()

    def test_init_without_c_drive_mounted(self):
        """Test that lowest lettered drive is selected when C is not mounted"""
        # Setup: Create a database with D and E drives mounted (no C)
        db = FSDatabase(self.db_path)
        db.upsert_volume(
            volume_key="5678EFGH-NTFS",
            root_path="D:\\",
            label="Data",
            filesystem="NTFS",
            serial_number="5678EFGH"
        )
        db.upsert_volume(
            volume_key="9ABC0123-NTFS",
            root_path="E:\\",
            label="Backup",
            filesystem="NTFS",
            serial_number="9ABC0123"
        )
        db.close()

        # Test: Create MockFiles and check cwd is D (lowest available)
        mock_fs = MockFiles(self.db_path)
        self.assertEqual(mock_fs.cwd, "D:\\")
        mock_fs.db.close()

    def test_init_with_unmounted_volumes(self):
        """Test that unmounted volumes (blank root_path) are ignored"""
        # Setup: Create volumes where C exists but is unmounted (blank root_path)
        db = FSDatabase(self.db_path)
        db.upsert_volume(
            volume_key="1234ABCD-NTFS",
            root_path="",  # Unmounted
            label="System",
            filesystem="NTFS",
            serial_number="1234ABCD"
        )
        db.upsert_volume(
            volume_key="5678EFGH-NTFS",
            root_path="E:\\",  # Mounted
            label="Data",
            filesystem="NTFS",
            serial_number="5678EFGH"
        )
        db.close()

        # Test: Should select E drive since C is unmounted
        mock_fs = MockFiles(self.db_path)
        self.assertEqual(mock_fs.cwd, "E:\\")
        mock_fs.db.close()

    def test_init_with_no_mounted_volumes(self):
        """Test default to C:\\ when no volumes are mounted"""
        # Setup: Create a database with no mounted volumes
        db = FSDatabase(self.db_path)
        db.upsert_volume(
            volume_key="1234ABCD-NTFS",
            root_path="",  # Unmounted
            label="System",
            filesystem="NTFS",
            serial_number="1234ABCD"
        )
        db.close()

        # Test: Should default to C:\\
        mock_fs = MockFiles(self.db_path)
        self.assertEqual(mock_fs.cwd, "C:\\")
        mock_fs.db.close()

    def test_init_with_empty_database(self):
        """Test default to C:\\ when database has no volumes"""
        # Setup: Create an empty database
        db = FSDatabase(self.db_path)
        db.close()

        # Test: Should default to C:\\
        mock_fs = MockFiles(self.db_path)
        self.assertEqual(mock_fs.cwd, "C:\\")
        mock_fs.db.close()


class TestMountVolume(unittest.TestCase):
    """Test the mount_volume() function"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name

    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_mount_volume_with_all_defaults(self):
        """Test mounting a volume with all default parameters"""
        mock_fs = MockFiles(self.db_path)

        # Mount first volume with defaults
        volume_id = mock_fs.mount_volume()

        # Verify it was created
        cursor = mock_fs.db.conn.cursor()
        cursor.execute("SELECT * FROM volumes WHERE id = ?", (volume_id,))
        vol = cursor.fetchone()

        self.assertIsNotNone(vol)
        self.assertEqual(vol['root_path'], "C:\\")
        self.assertEqual(vol['label'], "Volume_C")
        self.assertEqual(vol['filesystem'], "NTFS")
        self.assertEqual(vol['serial_number'], "10000000")
        self.assertEqual(vol['volume_key'], "10000000-NTFS")

        mock_fs.db.close()

    def test_mount_multiple_volumes_auto_increment(self):
        """Test that auto-generated drive letters increment correctly"""
        mock_fs = MockFiles(self.db_path)

        # Mount three volumes with defaults
        id1 = mock_fs.mount_volume()
        id2 = mock_fs.mount_volume()
        id3 = mock_fs.mount_volume()

        # Check they got C, D, E
        cursor = mock_fs.db.conn.cursor()
        cursor.execute("SELECT root_path FROM volumes ORDER BY id")
        paths = [row['root_path'] for row in cursor.fetchall()]

        self.assertEqual(paths, ["C:\\", "D:\\", "E:\\"])

        mock_fs.db.close()

    def test_mount_volume_with_custom_drive_letter(self):
        """Test mounting a volume with a specific drive letter"""
        mock_fs = MockFiles(self.db_path)

        volume_id = mock_fs.mount_volume(drive_letter='F')

        cursor = mock_fs.db.conn.cursor()
        cursor.execute("SELECT * FROM volumes WHERE id = ?", (volume_id,))
        vol = cursor.fetchone()

        self.assertEqual(vol['root_path'], "F:\\")
        self.assertEqual(vol['label'], "Volume_F")

        mock_fs.db.close()

    def test_mount_volume_with_all_custom_params(self):
        """Test mounting a volume with all custom parameters"""
        mock_fs = MockFiles(self.db_path)

        volume_id = mock_fs.mount_volume(
            drive_letter='Z',
            label='MyData',
            filesystem='exFAT',
            serial_number='ABCD1234'
        )

        cursor = mock_fs.db.conn.cursor()
        cursor.execute("SELECT * FROM volumes WHERE id = ?", (volume_id,))
        vol = cursor.fetchone()

        self.assertEqual(vol['root_path'], "Z:\\")
        self.assertEqual(vol['label'], "MyData")
        self.assertEqual(vol['filesystem'], "exFAT")
        self.assertEqual(vol['serial_number'], "ABCD1234")
        self.assertEqual(vol['volume_key'], "ABCD1234-exFAT")

        mock_fs.db.close()

    def test_mount_volume_serial_numbers_increment(self):
        """Test that auto-generated serial numbers increment"""
        mock_fs = MockFiles(self.db_path)

        mock_fs.mount_volume()
        mock_fs.mount_volume()

        cursor = mock_fs.db.conn.cursor()
        cursor.execute("SELECT serial_number FROM volumes ORDER BY id")
        serials = [row['serial_number'] for row in cursor.fetchall()]

        self.assertEqual(serials, ["10000000", "10000001"])

        mock_fs.db.close()

    def test_mount_volume_lowercase_drive_letter_converted(self):
        """Test that lowercase drive letters are converted to uppercase"""
        mock_fs = MockFiles(self.db_path)

        volume_id = mock_fs.mount_volume(drive_letter='d')

        cursor = mock_fs.db.conn.cursor()
        cursor.execute("SELECT root_path FROM volumes WHERE id = ?", (volume_id,))
        vol = cursor.fetchone()

        self.assertEqual(vol['root_path'], "D:\\")

        mock_fs.db.close()


class TestDirectoryOperations(unittest.TestCase):
    """Test directory operations: getcwd, cd, mkdir, rmdir"""

    def setUp(self):
        """Create a temporary database and mock filesystem for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.mock_fs = MockFiles(self.db_path)
        # Mount a C drive for testing
        self.mock_fs.mount_volume(drive_letter='C')

    def tearDown(self):
        """Clean up temporary database"""
        self.mock_fs.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_getcwd(self):
        """Test getting current working directory"""
        cwd = self.mock_fs.getcwd()
        self.assertEqual(cwd, "C:\\")

    def test_mkdir_absolute_path(self):
        """Test creating a directory with absolute path"""
        self.mock_fs.mkdir("C:\\Users")

        # Verify it exists in database
        cursor = self.mock_fs.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM directories WHERE dir_path = ?
        """, ("C:/Users",))
        self.assertIsNotNone(cursor.fetchone())

    def test_mkdir_with_parents(self):
        """Test creating nested directories (mkdir -p behavior)"""
        self.mock_fs.mkdir("C:\\Users\\Bob\\Documents")

        # Verify all directories were created
        cursor = self.mock_fs.db.conn.cursor()
        cursor.execute("SELECT dir_path FROM directories ORDER BY dir_path")
        paths = [row['dir_path'] for row in cursor.fetchall()]

        self.assertIn("C:/Users", paths)
        self.assertIn("C:/Users/Bob", paths)
        self.assertIn("C:/Users/Bob/Documents", paths)

    def test_mkdir_relative_path(self):
        """Test creating directory with relative path"""
        self.mock_fs.cd("C:\\")
        self.mock_fs.mkdir("Users")

        cursor = self.mock_fs.db.conn.cursor()
        cursor.execute("SELECT * FROM directories WHERE dir_path = ?", ("C:/Users",))
        self.assertIsNotNone(cursor.fetchone())

    def test_mkdir_without_parents_fails(self):
        """Test that mkdir without parents fails if parent doesn't exist"""
        with self.assertRaises(ValueError):
            self.mock_fs.mkdir("C:\\Users\\Bob\\Documents", parents=False)

    def test_cd_absolute_path(self):
        """Test changing to absolute path"""
        self.mock_fs.mkdir("C:\\Users\\Bob")
        self.mock_fs.cd("C:\\Users\\Bob")
        self.assertEqual(self.mock_fs.getcwd(), "C:\\Users\\Bob")

    def test_cd_relative_path(self):
        """Test changing to relative path"""
        self.mock_fs.mkdir("C:\\Users\\Bob")
        self.mock_fs.cd("C:\\")
        self.mock_fs.cd("Users")
        self.assertEqual(self.mock_fs.getcwd(), "C:\\Users")

    def test_cd_parent_directory(self):
        """Test changing to parent directory using .."""
        self.mock_fs.mkdir("C:\\Users\\Bob")
        self.mock_fs.cd("C:\\Users\\Bob")
        self.mock_fs.cd("..")
        self.assertEqual(self.mock_fs.getcwd(), "C:\\Users")

    def test_cd_to_root(self):
        """Test changing to root directory"""
        self.mock_fs.mkdir("C:\\Users")
        self.mock_fs.cd("C:\\Users")
        self.mock_fs.cd("C:\\")
        self.assertEqual(self.mock_fs.getcwd(), "C:\\")

    def test_cd_nonexistent_directory_fails(self):
        """Test that cd to non-existent directory fails"""
        with self.assertRaises(ValueError):
            self.mock_fs.cd("C:\\NonExistent")

    def test_cd_with_forward_slashes(self):
        """Test that cd handles forward slashes"""
        self.mock_fs.mkdir("C:\\Users\\Bob")
        self.mock_fs.cd("C:/Users/Bob")
        self.assertEqual(self.mock_fs.getcwd(), "C:\\Users\\Bob")

    def test_rmdir_empty_directory(self):
        """Test removing an empty directory"""
        self.mock_fs.mkdir("C:\\Temp")
        self.mock_fs.rmdir("C:\\Temp")

        # Verify it's gone
        cursor = self.mock_fs.db.conn.cursor()
        cursor.execute("SELECT * FROM directories WHERE dir_path = ?", ("C:/Temp",))
        self.assertIsNone(cursor.fetchone())

    def test_rmdir_nonempty_directory_fails(self):
        """Test that removing non-empty directory fails"""
        self.mock_fs.mkdir("C:\\Users\\Bob")

        # Try to remove parent - should fail because it has subdirectory
        with self.assertRaises(ValueError):
            self.mock_fs.rmdir("C:\\Users")

    def test_rmdir_relative_path(self):
        """Test removing directory with relative path"""
        self.mock_fs.mkdir("C:\\Temp")
        self.mock_fs.cd("C:\\")
        self.mock_fs.rmdir("Temp")

        cursor = self.mock_fs.db.conn.cursor()
        cursor.execute("SELECT * FROM directories WHERE dir_path = ?", ("C:/Temp",))
        self.assertIsNone(cursor.fetchone())

    def test_rmdir_nonexistent_fails(self):
        """Test that removing non-existent directory fails"""
        with self.assertRaises(ValueError):
            self.mock_fs.rmdir("C:\\NonExistent")

    def test_mkdir_already_exists(self):
        """Test that mkdir on existing directory is idempotent"""
        self.mock_fs.mkdir("C:\\Users")
        self.mock_fs.mkdir("C:\\Users")  # Should not error

        # Should still only have one entry
        cursor = self.mock_fs.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM directories WHERE dir_path = ?", ("C:/Users",))
        count = cursor.fetchone()['count']
        self.assertEqual(count, 1)


class TestSetFileDefaults(unittest.TestCase):
    """Test the set_file_defaults() function"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.mock_fs = MockFiles(self.db_path)
        self.mock_fs.mount_volume(drive_letter='C')

    def tearDown(self):
        """Clean up temporary database"""
        self.mock_fs.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_set_extension_default(self):
        """Test setting extension default"""
        self.mock_fs.set_file_defaults(extension='txt')
        defaults = self.mock_fs.get_file_defaults()
        self.assertEqual(defaults['extension'], 'txt')

    def test_set_size_default(self):
        """Test setting size_bytes default"""
        self.mock_fs.set_file_defaults(size_bytes=1024)
        defaults = self.mock_fs.get_file_defaults()
        self.assertEqual(defaults['size_bytes'], 1024)

    def test_set_multiple_defaults(self):
        """Test setting multiple defaults at once"""
        self.mock_fs.set_file_defaults(
            extension='doc',
            size_bytes=2048,
            readonly=1
        )
        defaults = self.mock_fs.get_file_defaults()
        self.assertEqual(defaults['extension'], 'doc')
        self.assertEqual(defaults['size_bytes'], 2048)
        self.assertEqual(defaults['readonly'], 1)

    def test_set_invalid_parameter_raises(self):
        """Test that setting unknown parameter raises ValueError"""
        with self.assertRaises(ValueError):
            self.mock_fs.set_file_defaults(invalid_param=123)


class TestSaveFunction(unittest.TestCase):
    """Test the save() function"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.mock_fs = MockFiles(self.db_path)
        self.mock_fs.mount_volume(drive_letter='C')

    def tearDown(self):
        """Clean up temporary database"""
        self.mock_fs.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_save_file_with_extension_in_name(self):
        """Test saving a file with extension in the name"""
        file_id = self.mock_fs.save("document.txt")
        self.assertIsInstance(file_id, int)
        self.assertGreater(file_id, 0)

    def test_save_file_creates_in_database(self):
        """Test that save creates the file in the database"""
        self.mock_fs.save("test.txt", size_bytes=1024)

        files = self.mock_fs.ls()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]['name'], 'test')
        self.assertEqual(files[0]['extension'], 'txt')
        self.assertEqual(files[0]['size_bytes'], 1024)

    def test_save_file_without_extension_uses_default(self):
        """Test that files without extension use the default"""
        self.mock_fs.set_file_defaults(extension='md')
        self.mock_fs.save("readme")

        files = self.mock_fs.ls()
        self.assertEqual(files[0]['extension'], 'md')

    def test_save_with_explicit_extension(self):
        """Test saving with explicit extension parameter"""
        self.mock_fs.save("myfile", extension='pdf')

        files = self.mock_fs.ls()
        self.assertEqual(files[0]['extension'], 'pdf')

    def test_save_with_empty_extension(self):
        """Test saving with explicitly no extension"""
        self.mock_fs.set_file_defaults(extension='txt')
        self.mock_fs.save("Makefile", extension='')

        files = self.mock_fs.ls()
        self.assertEqual(files[0]['name'], 'Makefile')
        self.assertEqual(files[0]['extension'], '')

    def test_save_extension_in_name_and_param_raises(self):
        """Test that extension in name AND as parameter raises error"""
        with self.assertRaises(ValueError):
            self.mock_fs.save("document.txt", extension='pdf')

    def test_save_updates_extension_default(self):
        """Test that save with extension updates the default"""
        self.mock_fs.save("first.pdf")
        self.mock_fs.save("second")  # Should use pdf as default

        files = self.mock_fs.ls()
        pdf_files = [f for f in files if f['extension'] == 'pdf']
        self.assertEqual(len(pdf_files), 2)

    def test_save_updates_size_default(self):
        """Test that save with size_bytes updates the default"""
        self.mock_fs.save("file1.txt", size_bytes=2048)
        self.mock_fs.save("file2.txt")  # Should use 2048 as default

        files = self.mock_fs.ls()
        self.assertEqual(files[0]['size_bytes'], 2048)
        self.assertEqual(files[1]['size_bytes'], 2048)

    def test_save_with_human_readable_time(self):
        """Test saving with human-readable mtime"""
        self.mock_fs.save("test.txt", mtime="2024-01-15 10:30:00")

        files = self.mock_fs.ls()
        self.assertIsNotNone(files[0]['mtime_ns'])
        self.assertIsInstance(files[0]['mtime_ns'], int)

    def test_save_in_subdirectory(self):
        """Test saving file after cd to subdirectory"""
        self.mock_fs.mkdir("C:\\Users\\Test")
        self.mock_fs.cd("C:\\Users\\Test")
        self.mock_fs.save("myfile.txt")

        files = self.mock_fs.ls()
        self.assertEqual(len(files), 1)

    def test_save_multiple_files(self):
        """Test saving multiple files"""
        self.mock_fs.save("file1.txt")
        self.mock_fs.save("file2.txt")
        self.mock_fs.save("file3.txt")

        files = self.mock_fs.ls()
        self.assertEqual(len(files), 3)

    def test_save_with_media_fields(self):
        """Test saving with media metadata"""
        self.mock_fs.save(
            "song.mp3",
            duration=180.5,
            bitrate=320000,
            codec='mp3'
        )

        files = self.mock_fs.ls()
        self.assertEqual(files[0]['duration'], 180.5)
        self.assertEqual(files[0]['bitrate'], 320000)
        self.assertEqual(files[0]['codec'], 'mp3')

    def test_save_with_tag_fields(self):
        """Test saving with tag metadata"""
        self.mock_fs.save(
            "song.mp3",
            tag_title="My Song",
            tag_artist="Artist Name"
        )

        files = self.mock_fs.ls()
        self.assertEqual(files[0]['tag_title'], "My Song")
        self.assertEqual(files[0]['tag_artist'], "Artist Name")


class TestLsFunction(unittest.TestCase):
    """Test the ls() function"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.mock_fs = MockFiles(self.db_path)
        self.mock_fs.mount_volume(drive_letter='C')

    def tearDown(self):
        """Clean up temporary database"""
        self.mock_fs.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_ls_empty_directory(self):
        """Test ls on empty directory"""
        files = self.mock_fs.ls()
        self.assertEqual(files, [])

    def test_ls_returns_all_files(self):
        """Test that ls returns all files in directory"""
        self.mock_fs.save("file1.txt")
        self.mock_fs.save("file2.txt")
        self.mock_fs.save("file3.doc")

        files = self.mock_fs.ls()
        self.assertEqual(len(files), 3)

    def test_ls_returns_file_info(self):
        """Test that ls returns complete file information"""
        self.mock_fs.save("test.txt", size_bytes=1024, readonly=1)

        files = self.mock_fs.ls()
        self.assertEqual(len(files), 1)
        file = files[0]
        self.assertEqual(file['name'], 'test')
        self.assertEqual(file['extension'], 'txt')
        self.assertEqual(file['size_bytes'], 1024)
        self.assertEqual(file['readonly'], 1)

    def test_ls_does_not_include_directories(self):
        """Test that ls only returns files, not directories"""
        self.mock_fs.save("file.txt")
        self.mock_fs.mkdir("C:\\Subdir")

        files = self.mock_fs.ls()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]['name'], 'file')

    def test_ls_after_cd(self):
        """Test ls after changing directory"""
        self.mock_fs.save("root_file.txt")
        self.mock_fs.mkdir("C:\\Users")
        self.mock_fs.cd("C:\\Users")
        self.mock_fs.save("users_file.txt")

        files = self.mock_fs.ls()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]['name'], 'users_file')

    def test_ls_sorted_by_name(self):
        """Test that ls results are sorted by name"""
        self.mock_fs.save("charlie.txt")
        self.mock_fs.save("alpha.txt")
        self.mock_fs.save("bravo.txt")

        files = self.mock_fs.ls()
        names = [f['name'] for f in files]
        self.assertEqual(names, ['alpha', 'bravo', 'charlie'])


class TestLsDirFunction(unittest.TestCase):
    """Test the ls_dir() function"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.mock_fs = MockFiles(self.db_path)
        self.mock_fs.mount_volume(drive_letter='C')

    def tearDown(self):
        """Clean up temporary database"""
        self.mock_fs.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_ls_dir_empty(self):
        """Test ls_dir on directory with no subdirectories"""
        subdirs = self.mock_fs.ls_dir()
        self.assertEqual(subdirs, [])

    def test_ls_dir_returns_immediate_children(self):
        """Test that ls_dir returns immediate subdirectories"""
        self.mock_fs.mkdir("C:\\Users")
        self.mock_fs.mkdir("C:\\Windows")
        self.mock_fs.mkdir("C:\\Program Files")

        subdirs = self.mock_fs.ls_dir()
        self.assertEqual(len(subdirs), 3)
        self.assertIn('Users', subdirs)
        self.assertIn('Windows', subdirs)
        self.assertIn('Program Files', subdirs)

    def test_ls_dir_not_recursive(self):
        """Test that ls_dir is not recursive"""
        self.mock_fs.mkdir("C:\\Users")
        self.mock_fs.mkdir("C:\\Users\\Bob")
        self.mock_fs.mkdir("C:\\Users\\Bob\\Documents")

        subdirs = self.mock_fs.ls_dir()
        self.assertEqual(subdirs, ['Users'])

    def test_ls_dir_after_cd(self):
        """Test ls_dir after changing directory"""
        self.mock_fs.mkdir("C:\\Users")
        self.mock_fs.mkdir("C:\\Users\\Bob")
        self.mock_fs.mkdir("C:\\Users\\Alice")
        self.mock_fs.cd("C:\\Users")

        subdirs = self.mock_fs.ls_dir()
        self.assertEqual(len(subdirs), 2)
        self.assertIn('Bob', subdirs)
        self.assertIn('Alice', subdirs)

    def test_ls_dir_does_not_include_files(self):
        """Test that ls_dir only returns directories, not files"""
        self.mock_fs.mkdir("C:\\Subdir")
        self.mock_fs.save("file.txt")

        subdirs = self.mock_fs.ls_dir()
        self.assertEqual(subdirs, ['Subdir'])

    def test_ls_dir_sorted(self):
        """Test that ls_dir results are sorted"""
        self.mock_fs.mkdir("C:\\Charlie")
        self.mock_fs.mkdir("C:\\Alpha")
        self.mock_fs.mkdir("C:\\Bravo")

        subdirs = self.mock_fs.ls_dir()
        self.assertEqual(subdirs, ['Alpha', 'Bravo', 'Charlie'])


class TestSaveM(unittest.TestCase):
    """Test the save_m() function for media files"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.mock_fs = MockFiles(self.db_path)
        self.mock_fs.mount_volume(drive_letter='C')

    def tearDown(self):
        """Clean up temporary database"""
        self.mock_fs.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_compute_size_from_duration_and_bitrate(self):
        """Test computing size_bytes from duration and bitrate"""
        self.mock_fs.save_m("song.mp3", duration=180, bitrate=320000)
        file = self.mock_fs.get_file("song.mp3")
        # size = 180 * 320000 / 8 = 7,200,000
        self.assertEqual(file['size_bytes'], 7200000)
        self.assertEqual(file['duration'], 180)
        self.assertEqual(file['bitrate'], 320000)

    def test_compute_duration_from_size_and_bitrate(self):
        """Test computing duration from size_bytes and bitrate"""
        self.mock_fs.save_m("track.mp3", size_bytes=4800000, bitrate=320000)
        file = self.mock_fs.get_file("track.mp3")
        # duration = 4800000 * 8 / 320000 = 120
        self.assertEqual(file['duration'], 120)
        self.assertEqual(file['size_bytes'], 4800000)

    def test_compute_bitrate_from_size_and_duration(self):
        """Test computing bitrate from size_bytes and duration"""
        self.mock_fs.save_m("audio.mp3", size_bytes=7200000, duration=180)
        file = self.mock_fs.get_file("audio.mp3")
        # bitrate = 7200000 * 8 / 180 = 320000
        self.assertEqual(file['bitrate'], 320000)

    def test_all_values_consistent_passes(self):
        """Test that consistent values pass validation"""
        # size = duration * bitrate / 8 = 180 * 320000 / 8 = 7200000
        file_id = self.mock_fs.save_m(
            "valid.mp3",
            size_bytes=7200000,
            duration=180,
            bitrate=320000
        )
        self.assertIsInstance(file_id, int)
        file = self.mock_fs.get_file("valid.mp3")
        self.assertEqual(file['size_bytes'], 7200000)

    def test_conflicting_values_raises_error(self):
        """Test that conflicting values raise ValueError"""
        # Expected size = 180 * 320000 / 8 = 7,200,000, but we provide 1000
        with self.assertRaises(ValueError) as ctx:
            self.mock_fs.save_m(
                "bad.mp3",
                size_bytes=1000,
                duration=180,
                bitrate=320000
            )
        self.assertIn("conflict", str(ctx.exception).lower())

    def test_tolerance_allows_small_differences(self):
        """Test that small differences within tolerance pass"""
        # Expected size = 7,200,000, provide 7,100,000 (~1.4% diff)
        file_id = self.mock_fs.save_m(
            "close.mp3",
            size_bytes=7100000,
            duration=180,
            bitrate=320000,
            tolerance=0.05  # 5% tolerance
        )
        self.assertIsInstance(file_id, int)

    def test_strict_tolerance_catches_small_differences(self):
        """Test that strict tolerance catches small differences"""
        with self.assertRaises(ValueError):
            self.mock_fs.save_m(
                "strict.mp3",
                size_bytes=7100000,
                duration=180,
                bitrate=320000,
                tolerance=0.01  # 1% tolerance - 1.4% diff will fail
            )

    def test_video_extension_computes_size(self):
        """Test that video files also compute size"""
        self.mock_fs.save_m("movie.mp4", duration=3600, bitrate=5000000)
        file = self.mock_fs.get_file("movie.mp4")
        # size = 3600 * 5000000 / 8 = 2,250,000,000
        self.assertEqual(file['size_bytes'], 2250000000)

    def test_image_requires_both_dimensions(self):
        """Test that images require both width and height"""
        with self.assertRaises(ValueError) as ctx:
            self.mock_fs.save_m("photo.jpg", resolution_width=1920)
        self.assertIn("resolution", str(ctx.exception).lower())

    def test_image_both_dimensions_works(self):
        """Test that images work with both dimensions"""
        file_id = self.mock_fs.save_m(
            "photo.jpg",
            resolution_width=1920,
            resolution_height=1080,
            size_bytes=500000
        )
        self.assertIsInstance(file_id, int)
        file = self.mock_fs.get_file("photo.jpg")
        self.assertEqual(file['resolution_width'], 1920)
        self.assertEqual(file['resolution_height'], 1080)

    def test_partial_values_no_computation(self):
        """Test that partial values don't cause errors when computation isn't possible"""
        # Only duration provided - can't compute anything else
        file_id = self.mock_fs.save_m("song.mp3", duration=180)
        self.assertIsInstance(file_id, int)
        file = self.mock_fs.get_file("song.mp3")
        self.assertEqual(file['duration'], 180)

    def test_preserves_other_media_fields(self):
        """Test that other media fields are preserved"""
        self.mock_fs.save_m(
            "song.mp3",
            duration=180,
            bitrate=320000,
            codec='mp3',
            sample_rate=44100,
            channels=2
        )
        file = self.mock_fs.get_file("song.mp3")
        self.assertEqual(file['codec'], 'mp3')
        self.assertEqual(file['sample_rate'], 44100)
        self.assertEqual(file['channels'], 2)

    def test_preserves_tag_fields(self):
        """Test that tag fields are preserved"""
        self.mock_fs.save_m(
            "song.mp3",
            duration=180,
            bitrate=320000,
            tag_title="My Song",
            tag_artist="Artist"
        )
        file = self.mock_fs.get_file("song.mp3")
        self.assertEqual(file['tag_title'], "My Song")
        self.assertEqual(file['tag_artist'], "Artist")

    def test_various_audio_extensions(self):
        """Test that various audio extensions are recognized"""
        for ext in ['mp3', 'wav', 'flac', 'aac', 'ogg']:
            self.mock_fs.save_m(f"test.{ext}", duration=60, bitrate=128000)
            file = self.mock_fs.get_file(f"test.{ext}")
            self.assertEqual(file['size_bytes'], 60 * 128000 // 8)

    def test_various_video_extensions(self):
        """Test that various video extensions are recognized"""
        for ext in ['mp4', 'avi', 'mkv', 'mov']:
            self.mock_fs.save_m(f"video.{ext}", duration=120, bitrate=1000000)
            file = self.mock_fs.get_file(f"video.{ext}")
            self.assertEqual(file['size_bytes'], 120 * 1000000 // 8)


class TestExists(unittest.TestCase):
    """Test the exists() function"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.mock_fs = MockFiles(self.db_path)
        self.mock_fs.mount_volume(drive_letter='C')

    def tearDown(self):
        """Clean up temporary database"""
        self.mock_fs.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_exists_file(self):
        """Test that exists returns True for a file"""
        self.mock_fs.save("test.txt")
        self.assertTrue(self.mock_fs.exists("test.txt"))

    def test_exists_directory(self):
        """Test that exists returns True for a directory"""
        self.mock_fs.mkdir("C:\\Users")
        self.assertTrue(self.mock_fs.exists("C:\\Users"))

    def test_exists_root_directory(self):
        """Test that exists returns True for root directory"""
        self.assertTrue(self.mock_fs.exists("C:\\"))

    def test_exists_nonexistent_file(self):
        """Test that exists returns False for non-existent file"""
        self.assertFalse(self.mock_fs.exists("nonexistent.txt"))

    def test_exists_nonexistent_directory(self):
        """Test that exists returns False for non-existent directory"""
        self.assertFalse(self.mock_fs.exists("C:\\NonExistent"))

    def test_exists_absolute_path(self):
        """Test exists with absolute path"""
        self.mock_fs.mkdir("C:\\Users")
        self.mock_fs.cd("C:\\Users")
        self.mock_fs.save("doc.txt")
        self.assertTrue(self.mock_fs.exists("C:\\Users\\doc.txt"))


class TestGetFile(unittest.TestCase):
    """Test the get_file() function"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.mock_fs = MockFiles(self.db_path)
        self.mock_fs.mount_volume(drive_letter='C')

    def tearDown(self):
        """Clean up temporary database"""
        self.mock_fs.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_get_file_by_relative_path(self):
        """Test getting file by relative path"""
        self.mock_fs.save("test.txt", size_bytes=1024)
        result = self.mock_fs.get_file("test.txt")
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'test')
        self.assertEqual(result['extension'], 'txt')
        self.assertEqual(result['size_bytes'], 1024)

    def test_get_file_by_absolute_path(self):
        """Test getting file by absolute path"""
        self.mock_fs.mkdir("C:\\Users")
        self.mock_fs.cd("C:\\Users")
        self.mock_fs.save("doc.pdf", size_bytes=2048)
        self.mock_fs.cd("C:\\")
        result = self.mock_fs.get_file("C:\\Users\\doc.pdf")
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'doc')
        self.assertEqual(result['extension'], 'pdf')

    def test_get_file_nonexistent(self):
        """Test getting non-existent file returns None"""
        result = self.mock_fs.get_file("nonexistent.txt")
        self.assertIsNone(result)

    def test_get_file_returns_all_fields(self):
        """Test that get_file returns all file fields"""
        self.mock_fs.save("test.txt", size_bytes=100, readonly=1)
        result = self.mock_fs.get_file("test.txt")
        self.assertIn('id', result)
        self.assertIn('name', result)
        self.assertIn('extension', result)
        self.assertIn('size_bytes', result)
        self.assertIn('readonly', result)


class TestDelete(unittest.TestCase):
    """Test the delete() function"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.mock_fs = MockFiles(self.db_path)
        self.mock_fs.mount_volume(drive_letter='C')

    def tearDown(self):
        """Clean up temporary database"""
        self.mock_fs.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_delete_file(self):
        """Test deleting a file"""
        self.mock_fs.save("test.txt")
        self.assertTrue(self.mock_fs.exists("test.txt"))
        result = self.mock_fs.delete("test.txt")
        self.assertTrue(result)
        self.assertFalse(self.mock_fs.exists("test.txt"))

    def test_delete_nonexistent(self):
        """Test deleting non-existent file returns False"""
        result = self.mock_fs.delete("nonexistent.txt")
        self.assertFalse(result)

    def test_rm_alias(self):
        """Test that rm is an alias for delete"""
        self.mock_fs.save("test.txt")
        result = self.mock_fs.rm("test.txt")
        self.assertTrue(result)
        self.assertFalse(self.mock_fs.exists("test.txt"))

    def test_delete_verify_gone(self):
        """Test that deleted file is gone from database"""
        self.mock_fs.save("test.txt")
        self.mock_fs.delete("test.txt")
        files = self.mock_fs.ls()
        self.assertEqual(len(files), 0)


class TestSetAttributes(unittest.TestCase):
    """Test the set_attributes() function"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.mock_fs = MockFiles(self.db_path)
        self.mock_fs.mount_volume(drive_letter='C')

    def tearDown(self):
        """Clean up temporary database"""
        self.mock_fs.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_set_size(self):
        """Test changing size_bytes"""
        self.mock_fs.save("test.txt", size_bytes=100)
        self.mock_fs.set_attributes("test.txt", size_bytes=500)
        result = self.mock_fs.get_file("test.txt")
        self.assertEqual(result['size_bytes'], 500)

    def test_set_readonly(self):
        """Test changing readonly flag"""
        self.mock_fs.save("test.txt", readonly=0)
        self.mock_fs.set_attributes("test.txt", readonly=1)
        result = self.mock_fs.get_file("test.txt")
        self.assertEqual(result['readonly'], 1)

    def test_set_timestamps(self):
        """Test changing timestamps"""
        self.mock_fs.save("test.txt")
        self.mock_fs.set_attributes("test.txt", mtime="2024-06-15 10:30:00")
        result = self.mock_fs.get_file("test.txt")
        self.assertIsNotNone(result['mtime_ns'])

    def test_set_multiple_attributes(self):
        """Test changing multiple attributes at once"""
        self.mock_fs.save("test.txt", size_bytes=100)
        self.mock_fs.set_attributes("test.txt", size_bytes=200, readonly=1, system=1)
        result = self.mock_fs.get_file("test.txt")
        self.assertEqual(result['size_bytes'], 200)
        self.assertEqual(result['readonly'], 1)
        self.assertEqual(result['system'], 1)

    def test_set_invalid_attribute_raises(self):
        """Test that invalid attribute names raise error"""
        self.mock_fs.save("test.txt")
        with self.assertRaises(ValueError):
            self.mock_fs.set_attributes("test.txt", invalid_attr=123)

    def test_set_nonexistent_file(self):
        """Test that set_attributes on non-existent file returns False"""
        result = self.mock_fs.set_attributes("nonexistent.txt", size_bytes=100)
        self.assertFalse(result)


class TestFind(unittest.TestCase):
    """Test the find() function"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.mock_fs = MockFiles(self.db_path)
        self.mock_fs.mount_volume(drive_letter='C')

    def tearDown(self):
        """Clean up temporary database"""
        self.mock_fs.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_find_star_extension(self):
        """Test finding files with *.txt pattern"""
        self.mock_fs.save("file1.txt")
        self.mock_fs.save("file2.txt")
        self.mock_fs.save("file3.doc")
        results = self.mock_fs.find("*.txt")
        self.assertEqual(len(results), 2)
        self.assertTrue(all('.txt' in r for r in results))

    def test_find_question_mark(self):
        """Test finding files with file?.txt pattern"""
        self.mock_fs.save("file1.txt")
        self.mock_fs.save("file2.txt")
        self.mock_fs.save("file10.txt")
        results = self.mock_fs.find("file?.txt")
        self.assertEqual(len(results), 2)

    def test_find_bracket_pattern(self):
        """Test finding files with [abc]* pattern"""
        self.mock_fs.save("alpha.txt")
        self.mock_fs.save("bravo.txt")
        self.mock_fs.save("charlie.txt")
        self.mock_fs.save("delta.txt")
        results = self.mock_fs.find("[abc]*")
        self.assertEqual(len(results), 3)

    def test_find_recursive(self):
        """Test that recursive=True finds files in subdirs"""
        self.mock_fs.save("root.txt")
        self.mock_fs.mkdir("C:\\subdir")
        self.mock_fs.cd("C:\\subdir")
        self.mock_fs.save("sub.txt")
        self.mock_fs.cd("C:\\")
        results = self.mock_fs.find("*.txt", path="C:\\", recursive=True)
        self.assertEqual(len(results), 2)

    def test_find_not_recursive(self):
        """Test that recursive=False only finds files in specified dir"""
        self.mock_fs.save("root.txt")
        self.mock_fs.mkdir("C:\\subdir")
        self.mock_fs.cd("C:\\subdir")
        self.mock_fs.save("sub.txt")
        self.mock_fs.cd("C:\\")
        results = self.mock_fs.find("*.txt", path="C:\\", recursive=False)
        self.assertEqual(len(results), 1)
        self.assertIn("root.txt", results[0])

    def test_find_specific_path(self):
        """Test find with specific path"""
        self.mock_fs.mkdir("C:\\docs")
        self.mock_fs.cd("C:\\docs")
        self.mock_fs.save("readme.txt")
        self.mock_fs.cd("C:\\")
        results = self.mock_fs.find("*.txt", path="C:\\docs")
        self.assertEqual(len(results), 1)


class TestCopy(unittest.TestCase):
    """Test the copy() function"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.mock_fs = MockFiles(self.db_path)
        self.mock_fs.mount_volume(drive_letter='C')

    def tearDown(self):
        """Clean up temporary database"""
        self.mock_fs.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_copy_single_file(self):
        """Test copying a single file"""
        self.mock_fs.save("file1.txt", size_bytes=100)
        count = self.mock_fs.copy("file1.txt", "file1_copy.txt")
        self.assertEqual(count, 1)
        self.assertTrue(self.mock_fs.exists("file1.txt"))
        self.assertTrue(self.mock_fs.exists("file1_copy.txt"))
        # Check content preserved
        copy = self.mock_fs.get_file("file1_copy.txt")
        self.assertEqual(copy['size_bytes'], 100)

    def test_copy_with_wildcard(self):
        """Test copying with wildcard pattern"""
        self.mock_fs.save("file1.txt")
        self.mock_fs.save("file2.txt")
        self.mock_fs.save("other.doc")
        self.mock_fs.mkdir("C:\\dest")
        count = self.mock_fs.copy("*.txt", "C:\\dest")
        self.assertEqual(count, 2)
        self.mock_fs.cd("C:\\dest")
        files = self.mock_fs.ls()
        self.assertEqual(len(files), 2)

    def test_copy_to_directory(self):
        """Test copying file to directory preserves name"""
        self.mock_fs.save("test.txt")
        self.mock_fs.mkdir("C:\\dest")
        self.mock_fs.copy("test.txt", "C:\\dest")
        self.assertTrue(self.mock_fs.exists("C:\\dest\\test.txt"))

    def test_copy_with_rename(self):
        """Test copying with rename"""
        self.mock_fs.save("original.txt", size_bytes=500)
        self.mock_fs.copy("original.txt", "renamed.txt")
        self.assertTrue(self.mock_fs.exists("original.txt"))
        self.assertTrue(self.mock_fs.exists("renamed.txt"))
        renamed = self.mock_fs.get_file("renamed.txt")
        self.assertEqual(renamed['name'], 'renamed')

    def test_copy_preserves_timestamps(self):
        """Test that copy preserves timestamps by default"""
        self.mock_fs.save("test.txt", mtime="2024-01-15 10:30:00")
        original = self.mock_fs.get_file("test.txt")
        self.mock_fs.copy("test.txt", "copy.txt")
        copy = self.mock_fs.get_file("copy.txt")
        self.assertEqual(original['mtime_ns'], copy['mtime_ns'])

    def test_copy_nonexistent_returns_zero(self):
        """Test copying non-existent file returns 0"""
        count = self.mock_fs.copy("nonexistent.txt", "dest.txt")
        self.assertEqual(count, 0)


class TestMove(unittest.TestCase):
    """Test the move() function"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.mock_fs = MockFiles(self.db_path)
        self.mock_fs.mount_volume(drive_letter='C')

    def tearDown(self):
        """Clean up temporary database"""
        self.mock_fs.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_move_single_file(self):
        """Test moving a single file"""
        self.mock_fs.save("file1.txt", size_bytes=100)
        self.mock_fs.mkdir("C:\\dest")
        count = self.mock_fs.move("file1.txt", "C:\\dest")
        self.assertEqual(count, 1)
        self.assertFalse(self.mock_fs.exists("C:\\file1.txt"))
        self.assertTrue(self.mock_fs.exists("C:\\dest\\file1.txt"))

    def test_move_with_wildcard(self):
        """Test moving with wildcard pattern"""
        self.mock_fs.save("file1.txt")
        self.mock_fs.save("file2.txt")
        self.mock_fs.mkdir("C:\\dest")
        count = self.mock_fs.move("*.txt", "C:\\dest")
        self.assertEqual(count, 2)
        files = self.mock_fs.ls()
        self.assertEqual(len(files), 0)

    def test_move_rename(self):
        """Test renaming (move to same dir with different name)"""
        self.mock_fs.save("old_name.txt", size_bytes=100)
        count = self.mock_fs.move("old_name.txt", "new_name.txt")
        self.assertEqual(count, 1)
        self.assertFalse(self.mock_fs.exists("old_name.txt"))
        self.assertTrue(self.mock_fs.exists("new_name.txt"))
        # Verify data preserved
        file = self.mock_fs.get_file("new_name.txt")
        self.assertEqual(file['size_bytes'], 100)

    def test_move_nonexistent_returns_zero(self):
        """Test moving non-existent file returns 0"""
        count = self.mock_fs.move("nonexistent.txt", "dest.txt")
        self.assertEqual(count, 0)


class TestCopydir(unittest.TestCase):
    """Test the copydir() function"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.mock_fs = MockFiles(self.db_path)
        self.mock_fs.mount_volume(drive_letter='C')

    def tearDown(self):
        """Clean up temporary database"""
        self.mock_fs.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_copydir_with_files(self):
        """Test copying directory with files"""
        self.mock_fs.mkdir("C:\\source")
        self.mock_fs.cd("C:\\source")
        self.mock_fs.save("file1.txt", size_bytes=100)
        self.mock_fs.save("file2.txt", size_bytes=200)
        self.mock_fs.cd("C:\\")
        count = self.mock_fs.copydir("C:\\source", "C:\\dest")
        self.assertEqual(count, 2)
        self.assertTrue(self.mock_fs.exists("C:\\dest\\file1.txt"))
        self.assertTrue(self.mock_fs.exists("C:\\dest\\file2.txt"))
        # Original still exists
        self.assertTrue(self.mock_fs.exists("C:\\source\\file1.txt"))

    def test_copydir_nested(self):
        """Test copying nested directories"""
        self.mock_fs.mkdir("C:\\source\\sub1\\sub2")
        self.mock_fs.cd("C:\\source")
        self.mock_fs.save("root.txt")
        self.mock_fs.cd("C:\\source\\sub1")
        self.mock_fs.save("level1.txt")
        self.mock_fs.cd("C:\\source\\sub1\\sub2")
        self.mock_fs.save("level2.txt")
        self.mock_fs.cd("C:\\")
        count = self.mock_fs.copydir("C:\\source", "C:\\dest")
        self.assertEqual(count, 3)
        self.assertTrue(self.mock_fs.exists("C:\\dest\\root.txt"))
        self.assertTrue(self.mock_fs.exists("C:\\dest\\sub1\\level1.txt"))
        self.assertTrue(self.mock_fs.exists("C:\\dest\\sub1\\sub2\\level2.txt"))

    def test_copydir_nonexistent_raises(self):
        """Test copying non-existent directory raises error"""
        with self.assertRaises(ValueError):
            self.mock_fs.copydir("C:\\nonexistent", "C:\\dest")


class TestMovedir(unittest.TestCase):
    """Test the movedir() function"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.mock_fs = MockFiles(self.db_path)
        self.mock_fs.mount_volume(drive_letter='C')

    def tearDown(self):
        """Clean up temporary database"""
        self.mock_fs.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_movedir_rename(self):
        """Test renaming directory"""
        self.mock_fs.mkdir("C:\\old_name")
        self.mock_fs.cd("C:\\old_name")
        self.mock_fs.save("test.txt")
        self.mock_fs.cd("C:\\")
        count = self.mock_fs.movedir("C:\\old_name", "C:\\new_name")
        self.assertEqual(count, 1)
        self.assertFalse(self.mock_fs.exists("C:\\old_name"))
        self.assertTrue(self.mock_fs.exists("C:\\new_name"))
        self.assertTrue(self.mock_fs.exists("C:\\new_name\\test.txt"))

    def test_movedir_to_different_location(self):
        """Test moving directory to different location"""
        self.mock_fs.mkdir("C:\\source")
        self.mock_fs.mkdir("C:\\parent")
        self.mock_fs.cd("C:\\source")
        self.mock_fs.save("file.txt")
        self.mock_fs.cd("C:\\")
        count = self.mock_fs.movedir("C:\\source", "C:\\parent\\source")
        self.assertEqual(count, 1)
        self.assertFalse(self.mock_fs.exists("C:\\source"))
        self.assertTrue(self.mock_fs.exists("C:\\parent\\source"))
        self.assertTrue(self.mock_fs.exists("C:\\parent\\source\\file.txt"))

    def test_movedir_files_move_with_directory(self):
        """Test that files move with directory"""
        self.mock_fs.mkdir("C:\\dir\\subdir")
        self.mock_fs.cd("C:\\dir")
        self.mock_fs.save("a.txt", size_bytes=100)
        self.mock_fs.cd("C:\\dir\\subdir")
        self.mock_fs.save("b.txt", size_bytes=200)
        self.mock_fs.cd("C:\\")
        count = self.mock_fs.movedir("C:\\dir", "C:\\renamed")
        self.assertEqual(count, 2)  # dir and subdir
        # Check files exist at new location
        self.assertTrue(self.mock_fs.exists("C:\\renamed\\a.txt"))
        self.assertTrue(self.mock_fs.exists("C:\\renamed\\subdir\\b.txt"))
        # Verify file data preserved
        file = self.mock_fs.get_file("C:\\renamed\\a.txt")
        self.assertEqual(file['size_bytes'], 100)

    def test_movedir_nonexistent_raises(self):
        """Test moving non-existent directory raises error"""
        with self.assertRaises(ValueError):
            self.mock_fs.movedir("C:\\nonexistent", "C:\\dest")


if __name__ == '__main__':
    unittest.main()