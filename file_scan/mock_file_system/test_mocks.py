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


if __name__ == '__main__':
    unittest.main()