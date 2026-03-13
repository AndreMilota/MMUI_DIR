# test_safe_files.py
"""
Tests for SafeFiles wrapper using MockFiles as the underlying filesystem.

These tests verify that SafeFiles correctly enforces PathGuard restrictions
without actually modifying any real files.
"""
from file_scan.mock_file_system.mock_files import MockFiles
from file_scan.path_guard import PathGuard
from file_scan.safe_files import SafeFiles


def test_safe_files_allows_permitted_operations():
    """Test that SafeFiles allows operations in permitted paths."""
    # Setup mock filesystem
    fs = MockFiles(":memory:")
    fs.mount_volume("C")
    fs.mkdir("C:/allowed")
    fs.cd("C:/allowed")

    # Setup guard - allow everything under C:/allowed
    guard = PathGuard()
    guard.allow("DISK001", "C:/allowed/**")

    # Wrap with SafeFiles
    safe_fs = SafeFiles(fs, guard, disk_id="DISK001")

    # Should be able to save files in allowed path
    safe_fs.cd("C:/allowed")
    file_id = safe_fs.save("test.txt")
    assert file_id is not None

    # File should exist
    assert safe_fs.exists("test.txt")

    # Should be able to delete
    result = safe_fs.delete("test.txt")
    assert result is True

    print("PASS: test_safe_files_allows_permitted_operations")


def test_safe_files_blocks_forbidden_operations():
    """Test that SafeFiles blocks operations in forbidden paths."""
    # Setup mock filesystem
    fs = MockFiles(":memory:")
    fs.mount_volume("C")
    fs.mkdir("C:/allowed")
    fs.mkdir("C:/allowed/forbidden")
    fs.cd("C:/allowed")

    # Setup guard - allow C:/allowed but deny C:/allowed/forbidden
    guard = PathGuard()
    guard.allow("DISK001", "C:/allowed/**")
    guard.deny("DISK001", "C:/allowed/forbidden/**")

    # Wrap with SafeFiles
    safe_fs = SafeFiles(fs, guard, disk_id="DISK001")

    # Should be able to save in allowed path
    safe_fs.cd("C:/allowed")
    safe_fs.save("allowed_file.txt")
    assert safe_fs.exists("allowed_file.txt")

    # Should NOT be able to save in forbidden path
    safe_fs.cd("C:/allowed/forbidden")
    try:
        safe_fs.save("forbidden_file.txt")
        assert False, "Should have raised PermissionError"
    except PermissionError as e:
        assert "PathGuard denied" in str(e)

    print("PASS: test_safe_files_blocks_forbidden_operations")


def test_safe_files_blocks_mkdir_in_forbidden():
    """Test that SafeFiles blocks mkdir in forbidden paths."""
    fs = MockFiles(":memory:")
    fs.mount_volume("C")
    fs.mkdir("C:/allowed")

    guard = PathGuard()
    guard.allow("DISK001", "C:/allowed/**")
    guard.deny("DISK001", "C:/allowed/forbidden/**")

    safe_fs = SafeFiles(fs, guard, disk_id="DISK001")

    # Should be able to mkdir in allowed path
    safe_fs.mkdir("C:/allowed/subdir")
    assert fs.exists("C:/allowed/subdir")

    # Should NOT be able to mkdir in forbidden path
    try:
        safe_fs.mkdir("C:/allowed/forbidden/subdir")
        assert False, "Should have raised PermissionError"
    except PermissionError as e:
        assert "PathGuard denied" in str(e)

    print("PASS: test_safe_files_blocks_mkdir_in_forbidden")


def test_safe_files_blocks_delete_in_forbidden():
    """Test that SafeFiles blocks delete in forbidden paths."""
    fs = MockFiles(":memory:")
    fs.mount_volume("C")
    fs.mkdir("C:/allowed/forbidden")
    fs.cd("C:/allowed/forbidden")
    fs.save("protected.txt")  # Create file directly in underlying fs

    guard = PathGuard()
    guard.allow("DISK001", "C:/allowed/**")
    guard.deny("DISK001", "C:/allowed/forbidden/**")

    safe_fs = SafeFiles(fs, guard, disk_id="DISK001")

    # File exists
    assert safe_fs.exists("C:/allowed/forbidden/protected.txt")

    # Should NOT be able to delete in forbidden path
    try:
        safe_fs.delete("C:/allowed/forbidden/protected.txt")
        assert False, "Should have raised PermissionError"
    except PermissionError as e:
        assert "PathGuard denied" in str(e)

    # File should still exist
    assert fs.exists("C:/allowed/forbidden/protected.txt")

    print("PASS: test_safe_files_blocks_delete_in_forbidden")


def test_safe_files_blocks_copy_to_forbidden():
    """Test that SafeFiles blocks copy operations to forbidden destinations."""
    fs = MockFiles(":memory:")
    fs.mount_volume("C")
    fs.mkdir("C:/allowed")
    fs.mkdir("C:/allowed/forbidden")
    fs.cd("C:/allowed")
    fs.save("source.txt")

    guard = PathGuard()
    guard.allow("DISK001", "C:/allowed/**")
    guard.deny("DISK001", "C:/allowed/forbidden/**")

    safe_fs = SafeFiles(fs, guard, disk_id="DISK001")

    # Should NOT be able to copy to forbidden destination
    try:
        safe_fs.copy("C:/allowed/source.txt", "C:/allowed/forbidden/dest.txt")
        assert False, "Should have raised PermissionError"
    except PermissionError as e:
        assert "PathGuard denied" in str(e)

    print("PASS: test_safe_files_blocks_copy_to_forbidden")


def test_safe_files_blocks_move_from_forbidden():
    """Test that SafeFiles blocks move operations from forbidden sources."""
    fs = MockFiles(":memory:")
    fs.mount_volume("C")
    fs.mkdir("C:/allowed")
    fs.mkdir("C:/allowed/forbidden")
    fs.cd("C:/allowed/forbidden")
    fs.save("protected.txt")
    fs.mkdir("C:/allowed/dest")

    guard = PathGuard()
    guard.allow("DISK001", "C:/allowed/**")
    guard.deny("DISK001", "C:/allowed/forbidden/**")

    safe_fs = SafeFiles(fs, guard, disk_id="DISK001")

    # Should NOT be able to move from forbidden source
    try:
        safe_fs.move("C:/allowed/forbidden/protected.txt", "C:/allowed/dest/moved.txt")
        assert False, "Should have raised PermissionError"
    except PermissionError as e:
        assert "PathGuard denied" in str(e)

    # File should still be in original location
    assert fs.exists("C:/allowed/forbidden/protected.txt")

    print("PASS: test_safe_files_blocks_move_from_forbidden")


def test_safe_files_can_change_respects_guard():
    """Test that can_change respects PathGuard restrictions."""
    fs = MockFiles(":memory:")
    fs.mount_volume("C")
    fs.mkdir("C:/allowed")
    fs.mkdir("C:/allowed/forbidden")
    fs.cd("C:/allowed")
    fs.save("allowed_file.txt")
    fs.cd("C:/allowed/forbidden")
    fs.save("forbidden_file.txt")

    guard = PathGuard()
    guard.allow("DISK001", "C:/allowed/**")
    guard.deny("DISK001", "C:/allowed/forbidden/**")

    safe_fs = SafeFiles(fs, guard, disk_id="DISK001")

    # can_change should return True for allowed path
    assert safe_fs.can_change("C:/allowed/allowed_file.txt") is True

    # can_change should return False for forbidden path
    assert safe_fs.can_change("C:/allowed/forbidden/forbidden_file.txt") is False

    print("PASS: test_safe_files_can_change_respects_guard")


def test_safe_files_read_operations_always_allowed():
    """Test that read operations work even in forbidden paths."""
    fs = MockFiles(":memory:")
    fs.mount_volume("C")
    fs.mkdir("C:/allowed/forbidden")
    fs.cd("C:/allowed/forbidden")
    fs.save("readable.txt")

    guard = PathGuard()
    guard.allow("DISK001", "C:/allowed/**")
    guard.deny("DISK001", "C:/allowed/forbidden/**")

    safe_fs = SafeFiles(fs, guard, disk_id="DISK001")

    # Read operations should work in forbidden paths
    assert safe_fs.exists("C:/allowed/forbidden/readable.txt") is True
    assert safe_fs.get_file("C:/allowed/forbidden/readable.txt") is not None

    # ls should work
    safe_fs.cd("C:/allowed/forbidden")
    files = safe_fs.ls()
    assert len(files) == 1

    # dir should work
    listing = safe_fs.dir("C:/allowed/forbidden")
    assert "readable.txt" in listing

    # find should work
    matches = safe_fs.find("*.txt", "C:/allowed/forbidden")
    assert len(matches) == 1

    print("PASS: test_safe_files_read_operations_always_allowed")


def test_safe_files_with_callable_disk_id():
    """Test SafeFiles with a callable disk_id function."""
    fs = MockFiles(":memory:")
    fs.mount_volume("C")
    fs.mount_volume("D")
    fs.mkdir("C:/data")
    fs.mkdir("D:/data")

    guard = PathGuard()
    guard.allow("C_DISK", "C:/**")
    guard.deny("D_DISK", "D:/**")  # D drive is completely denied

    # Callable that extracts disk_id from path
    def get_disk_id(path: str) -> str:
        if path.upper().startswith("C:"):
            return "C_DISK"
        elif path.upper().startswith("D:"):
            return "D_DISK"
        return "UNKNOWN"

    safe_fs = SafeFiles(fs, guard, disk_id=get_disk_id)

    # Should be able to save on C:
    safe_fs.cd("C:/data")
    safe_fs.save("c_file.txt")
    assert safe_fs.exists("C:/data/c_file.txt")

    # Should NOT be able to save on D:
    safe_fs.cd("D:/data")
    try:
        safe_fs.save("d_file.txt")
        assert False, "Should have raised PermissionError"
    except PermissionError:
        pass

    print("PASS: test_safe_files_with_callable_disk_id")


def test_safe_files_default_deny():
    """Test that SafeFiles denies operations when no rules match (default deny)."""
    fs = MockFiles(":memory:")
    fs.mount_volume("C")
    fs.mkdir("C:/unregistered")
    fs.cd("C:/unregistered")

    # Empty guard - no rules
    guard = PathGuard()

    safe_fs = SafeFiles(fs, guard, disk_id="DISK001")

    # Should NOT be able to save (no allow rules)
    try:
        safe_fs.save("file.txt")
        assert False, "Should have raised PermissionError"
    except PermissionError as e:
        assert "PathGuard denied" in str(e)

    print("PASS: test_safe_files_default_deny")


def run_all_tests():
    """Run all SafeFiles tests."""
    print("=" * 60)
    print("Running SafeFiles tests with MockFiles")
    print("=" * 60)

    test_safe_files_allows_permitted_operations()
    test_safe_files_blocks_forbidden_operations()
    test_safe_files_blocks_mkdir_in_forbidden()
    test_safe_files_blocks_delete_in_forbidden()
    test_safe_files_blocks_copy_to_forbidden()
    test_safe_files_blocks_move_from_forbidden()
    test_safe_files_can_change_respects_guard()
    test_safe_files_read_operations_always_allowed()
    test_safe_files_with_callable_disk_id()
    test_safe_files_default_deny()

    print("=" * 60)
    print("All SafeFiles tests PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()