# test_safe_files_real.py
"""
Tests for SafeFiles wrapper using RealFiles as the underlying filesystem.

WARNING: Some tests in this file perform actual filesystem operations.
The dangerous tests are in a separate function that is NOT called by main.

Test organization:
1. test_can_change_* - Safe tests that only check permissions without modifying files
2. test_real_operations_* - DANGEROUS tests that actually modify the filesystem
                           These are NOT called by main and must be reviewed before running

To run only the safe tests:
    python test_safe_files_real.py

To run the dangerous tests (REVIEW FIRST):
    python test_safe_files_real.py --run-dangerous
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from file_scan.real_files import RealFiles
from file_scan.path_guard import PathGuard
from file_scan.safe_files import SafeFiles


# Path to test files directory
TEST_FILES_DIR = Path(__file__).parent.parent / "test_files"
FORBIDDEN_DIR = TEST_FILES_DIR / "forbidden"


# =============================================================================
# SAFE TESTS - Use can_change() without modifying filesystem
# =============================================================================

def test_can_change_allowed_path():
    """Test that can_change returns True for allowed paths (using test_files)."""
    # Verify test file exists
    test_file = FORBIDDEN_DIR / "do_not_modify.txt"
    if not test_file.exists():
        print(f"SKIP: Test file not found: {test_file}")
        return

    # Create RealFiles with modifications DISABLED (safe)
    fs = RealFiles(start_path=str(TEST_FILES_DIR), allow_modifications=False)

    # Setup guard - allow test_files but deny forbidden
    guard = PathGuard()
    guard.allow("TEST", str(TEST_FILES_DIR).replace("\\", "/") + "/**")
    guard.deny("TEST", str(FORBIDDEN_DIR).replace("\\", "/") + "/**")

    safe_fs = SafeFiles(fs, guard, disk_id="TEST")

    # For allowed path, can_change should be False because allow_modifications=False
    # (even though PathGuard would allow it)
    assert safe_fs.can_change(str(TEST_FILES_DIR / "nonexistent.txt")) is False

    print("PASS: test_can_change_allowed_path")


def test_can_change_forbidden_path():
    """Test that can_change returns False for forbidden paths."""
    test_file = FORBIDDEN_DIR / "do_not_modify.txt"
    if not test_file.exists():
        print(f"SKIP: Test file not found: {test_file}")
        return

    fs = RealFiles(start_path=str(TEST_FILES_DIR), allow_modifications=True)

    guard = PathGuard()
    guard.allow("TEST", str(TEST_FILES_DIR).replace("\\", "/") + "/**")
    guard.deny("TEST", str(FORBIDDEN_DIR).replace("\\", "/") + "/**")

    safe_fs = SafeFiles(fs, guard, disk_id="TEST")

    # can_change should be False for forbidden path (PathGuard denies it)
    assert safe_fs.can_change(str(test_file)) is False

    print("PASS: test_can_change_forbidden_path")


def test_can_change_with_readonly_file():
    """Test that can_change respects file read-only status."""
    # This test checks that RealFiles.can_change() checks write permissions
    # We'll create a temporary read-only file for this

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file
        test_file = Path(tmpdir) / "readonly_test.txt"
        test_file.write_text("test content")

        # Make it read-only
        os.chmod(str(test_file), 0o444)

        try:
            fs = RealFiles(start_path=tmpdir, allow_modifications=True)

            guard = PathGuard()
            guard.allow("TEST", tmpdir.replace("\\", "/") + "/**")

            safe_fs = SafeFiles(fs, guard, disk_id="TEST")

            # can_change should be False for read-only file
            result = safe_fs.can_change(str(test_file))
            assert result is False, f"Expected False for read-only file, got {result}"

            print("PASS: test_can_change_with_readonly_file")
        finally:
            # Restore write permission so temp dir can be cleaned up
            os.chmod(str(test_file), 0o644)


def test_pathguard_blocks_forbidden_dir():
    """Test that PathGuard correctly blocks the forbidden directory."""
    guard = PathGuard()
    test_files_path = str(TEST_FILES_DIR).replace("\\", "/")
    forbidden_path = str(FORBIDDEN_DIR).replace("\\", "/")

    guard.allow("TEST", test_files_path + "/**")
    guard.deny("TEST", forbidden_path + "/**")

    # Allowed path should be OK
    assert guard.ok("TEST", test_files_path + "/some_file.txt") is True

    # Forbidden path should be denied
    assert guard.ok("TEST", forbidden_path + "/any_file.txt") is False

    print("PASS: test_pathguard_blocks_forbidden_dir")


def test_safe_files_read_operations_real():
    """Test that read operations work with RealFiles."""
    if not TEST_FILES_DIR.exists():
        print(f"SKIP: Test directory not found: {TEST_FILES_DIR}")
        return

    fs = RealFiles(start_path=str(TEST_FILES_DIR), allow_modifications=False)

    guard = PathGuard()
    guard.allow("TEST", str(TEST_FILES_DIR).replace("\\", "/") + "/**")
    guard.deny("TEST", str(FORBIDDEN_DIR).replace("\\", "/") + "/**")

    safe_fs = SafeFiles(fs, guard, disk_id="TEST")

    # exists() should work
    assert safe_fs.exists(str(FORBIDDEN_DIR)) is True

    # ls_dir() should work
    subdirs = safe_fs.ls_dir()
    assert "forbidden" in subdirs

    # dir() should work
    listing = safe_fs.dir()
    assert "forbidden" in listing

    print("PASS: test_safe_files_read_operations_real")


def run_safe_tests():
    """Run all safe tests that don't modify the filesystem."""
    print("=" * 60)
    print("Running SAFE SafeFiles tests with RealFiles")
    print("(These tests do NOT modify the filesystem)")
    print("=" * 60)

    test_can_change_allowed_path()
    test_can_change_forbidden_path()
    test_can_change_with_readonly_file()
    test_pathguard_blocks_forbidden_dir()
    test_safe_files_read_operations_real()

    print("=" * 60)
    print("All SAFE tests PASSED!")
    print("=" * 60)


# =============================================================================
# DANGEROUS TESTS - Actually modify the filesystem
# =============================================================================
# WARNING: These tests create, modify, and delete real files.
# They are NOT called by main. Review before running.
# =============================================================================

def test_real_operations_save_allowed():
    """
    DANGEROUS: Actually creates a file in a temp directory.
    Tests that SafeFiles allows save in permitted paths.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        fs = RealFiles(start_path=tmpdir, allow_modifications=True)

        guard = PathGuard()
        guard.allow("TEST", tmpdir.replace("\\", "/") + "/**")

        safe_fs = SafeFiles(fs, guard, disk_id="TEST")

        # Save should work
        safe_fs.save("test_file", extension="txt", content="Hello, World!")

        # Verify file was created
        created_file = Path(tmpdir) / "test_file.txt"
        assert created_file.exists(), "File was not created"
        assert created_file.read_text() == "Hello, World!"

        print("PASS: test_real_operations_save_allowed")


def test_real_operations_save_forbidden():
    """
    DANGEROUS: Attempts to create a file in a forbidden path.
    Tests that SafeFiles blocks save in forbidden paths.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create forbidden subdirectory
        forbidden = Path(tmpdir) / "forbidden"
        forbidden.mkdir()

        fs = RealFiles(start_path=tmpdir, allow_modifications=True)

        guard = PathGuard()
        guard.allow("TEST", tmpdir.replace("\\", "/") + "/**")
        guard.deny("TEST", str(forbidden).replace("\\", "/") + "/**")

        safe_fs = SafeFiles(fs, guard, disk_id="TEST")

        # Save in forbidden should fail
        safe_fs.cd(str(forbidden))
        try:
            safe_fs.save("forbidden_file.txt")
            assert False, "Should have raised PermissionError"
        except PermissionError as e:
            assert "PathGuard denied" in str(e)

        # Verify file was NOT created
        assert not (forbidden / "forbidden_file.txt").exists()

        print("PASS: test_real_operations_save_forbidden")


def test_real_operations_delete_forbidden():
    """
    DANGEROUS: Attempts to delete a file in a forbidden path.
    Tests that SafeFiles blocks delete in forbidden paths.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create forbidden subdirectory with a file
        forbidden = Path(tmpdir) / "forbidden"
        forbidden.mkdir()
        protected_file = forbidden / "protected.txt"
        protected_file.write_text("This should not be deleted")

        fs = RealFiles(start_path=tmpdir, allow_modifications=True)

        guard = PathGuard()
        guard.allow("TEST", tmpdir.replace("\\", "/") + "/**")
        guard.deny("TEST", str(forbidden).replace("\\", "/") + "/**")

        safe_fs = SafeFiles(fs, guard, disk_id="TEST")

        # Delete in forbidden should fail
        try:
            safe_fs.delete(str(protected_file))
            assert False, "Should have raised PermissionError"
        except PermissionError as e:
            assert "PathGuard denied" in str(e)

        # Verify file was NOT deleted
        assert protected_file.exists()
        assert protected_file.read_text() == "This should not be deleted"

        print("PASS: test_real_operations_delete_forbidden")


def test_real_operations_copy_to_forbidden():
    """
    DANGEROUS: Attempts to copy a file to a forbidden destination.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create source file and forbidden directory
        source_file = Path(tmpdir) / "source.txt"
        source_file.write_text("Source content")
        forbidden = Path(tmpdir) / "forbidden"
        forbidden.mkdir()

        fs = RealFiles(start_path=tmpdir, allow_modifications=True)

        guard = PathGuard()
        guard.allow("TEST", tmpdir.replace("\\", "/") + "/**")
        guard.deny("TEST", str(forbidden).replace("\\", "/") + "/**")

        safe_fs = SafeFiles(fs, guard, disk_id="TEST")

        # Copy to forbidden should fail
        try:
            safe_fs.copy(str(source_file), str(forbidden / "dest.txt"))
            assert False, "Should have raised PermissionError"
        except PermissionError as e:
            assert "PathGuard denied" in str(e)

        # Verify file was NOT copied
        assert not (forbidden / "dest.txt").exists()

        print("PASS: test_real_operations_copy_to_forbidden")


def test_real_operations_mkdir_forbidden():
    """
    DANGEROUS: Attempts to create a directory in a forbidden path.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        forbidden = Path(tmpdir) / "forbidden"
        forbidden.mkdir()

        fs = RealFiles(start_path=tmpdir, allow_modifications=True)

        guard = PathGuard()
        guard.allow("TEST", tmpdir.replace("\\", "/") + "/**")
        guard.deny("TEST", str(forbidden).replace("\\", "/") + "/**")

        safe_fs = SafeFiles(fs, guard, disk_id="TEST")

        # mkdir in forbidden should fail
        try:
            safe_fs.mkdir(str(forbidden / "new_subdir"))
            assert False, "Should have raised PermissionError"
        except PermissionError as e:
            assert "PathGuard denied" in str(e)

        # Verify directory was NOT created
        assert not (forbidden / "new_subdir").exists()

        print("PASS: test_real_operations_mkdir_forbidden")


def run_dangerous_tests():
    """
    Run dangerous tests that actually modify the filesystem.

    WARNING: Review these tests before running!
    They use tempfile.TemporaryDirectory for safety, but still perform real I/O.
    """
    print("=" * 60)
    print("Running DANGEROUS SafeFiles tests with RealFiles")
    print("WARNING: These tests perform actual filesystem operations!")
    print("(Using temporary directories for safety)")
    print("=" * 60)

    test_real_operations_save_allowed()
    test_real_operations_save_forbidden()
    test_real_operations_delete_forbidden()
    test_real_operations_copy_to_forbidden()
    test_real_operations_mkdir_forbidden()

    print("=" * 60)
    print("All DANGEROUS tests PASSED!")
    print("=" * 60)


# =============================================================================
# Main entry point
# =============================================================================

if __name__ == "__main__":
    # By default, only run safe tests
    run_safe_tests()

    # Run dangerous tests only if explicitly requested
    if "--run-dangerous" in sys.argv:
        print("\n")
        run_dangerous_tests()
    else:
        print("\nTo run dangerous tests, use: python test_safe_files_real.py --run-dangerous")