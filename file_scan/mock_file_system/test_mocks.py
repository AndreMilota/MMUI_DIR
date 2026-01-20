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


if __name__ == '__main__':
    unittest.main()