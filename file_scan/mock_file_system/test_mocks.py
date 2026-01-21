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


if __name__ == '__main__':
    unittest.main()