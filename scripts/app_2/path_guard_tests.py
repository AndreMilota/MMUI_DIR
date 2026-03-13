# Tests for the PathGuard class
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from file_scan.path_guard import PathGuard


def test_default_deny():
    """Test that everything is denied by default (no rules)."""
    pg = PathGuard()

    # Any path should be denied by default
    assert pg.ok("DISK001", "any/path/file.txt") == False
    assert pg.ok("DISK999", "another/path") == False

    print("PASS: test_default_deny")


def test_basic_allow():
    """Test basic allow functionality."""
    pg = PathGuard()

    # Allow a directory
    pg.allow("DISK001", "photos")

    # File in allowed directory should be ok
    assert pg.ok("DISK001", "photos/pic.jpg") == True
    assert pg.ok("DISK001", "photos/vacation/pic.jpg") == True

    # File outside allowed directory should still be denied
    assert pg.ok("DISK001", "documents/file.txt") == False

    # Different disk should still be denied
    assert pg.ok("DISK002", "photos/pic.jpg") == False

    print("PASS: test_basic_allow")


def test_allow_with_backslashes():
    """Test that backslashes are normalized to forward slashes."""
    pg = PathGuard()

    # Use backslashes in allow
    pg.allow("DISK001", "photos\\vacation")

    # Should match paths with forward slashes
    assert pg.ok("DISK001", "photos/vacation/pic.jpg") == True

    # Should also match paths with backslashes
    assert pg.ok("DISK001", "photos\\vacation\\pic.jpg") == True

    print("PASS: test_allow_with_backslashes")


def test_deny_exception():
    """Test that deny creates exceptions within allowed paths."""
    pg = PathGuard()

    # Allow a directory
    pg.allow("DISK001", "documents")

    # Deny a subdirectory
    pg.deny("DISK001", "documents/private")

    # Allowed path should be ok
    assert pg.ok("DISK001", "documents/public/file.txt") == True

    # Denied path should not be ok
    assert pg.ok("DISK001", "documents/private/file.txt") == False

    # Files in subdirectories of denied path should also be blocked
    assert pg.ok("DISK001", "documents/private/secret/file.txt") == False

    print("PASS: test_deny_exception")


def test_allow_within_deny():
    """Test that you can re-allow within a denied path."""
    pg = PathGuard()

    # Allow documents
    pg.allow("DISK001", "documents")

    # Deny private
    pg.deny("DISK001", "documents/private")

    # Re-allow shared within private
    pg.allow("DISK001", "documents/private/shared")

    # Private is blocked
    assert pg.ok("DISK001", "documents/private/secret.txt") == False

    # But shared within private is allowed
    assert pg.ok("DISK001", "documents/private/shared/file.txt") == True

    print("PASS: test_allow_within_deny")


def test_wildcard_single_star():
    """Test single * wildcard matching."""
    pg = PathGuard()

    # Allow all .txt files in a directory
    pg.allow("DISK001", "docs/*.txt")

    # TXT files should be ok
    assert pg.ok("DISK001", "docs/readme.txt") == True

    # Other file types should be denied
    assert pg.ok("DISK001", "docs/image.png") == False

    # TXT in subdirectory should be denied (single * doesn't cross directories)
    assert pg.ok("DISK001", "docs/sub/readme.txt") == False

    print("PASS: test_wildcard_single_star")


def test_wildcard_double_star():
    """Test ** recursive wildcard matching."""
    pg = PathGuard()

    # Allow all .mp3 files recursively
    pg.allow("DISK001", "music/**/*.mp3")

    # MP3 files at any depth should be ok
    assert pg.ok("DISK001", "music/song.mp3") == True
    assert pg.ok("DISK001", "music/rock/song.mp3") == True
    assert pg.ok("DISK001", "music/rock/classic/song.mp3") == True

    # Other file types should be denied
    assert pg.ok("DISK001", "music/rock/playlist.m3u") == False

    print("PASS: test_wildcard_double_star")


def test_query_with_wildcards_conservative():
    """Test that queries with wildcards are conservative (deny if ambiguous)."""
    pg = PathGuard()

    # Allow a directory but deny a subdirectory
    pg.allow("DISK001", "documents")
    pg.deny("DISK001", "documents/private")

    # Query with wildcard that could match denied path should be denied
    assert pg.ok("DISK001", "documents/*") == False

    # Query with wildcard outside any deny rules
    pg2 = PathGuard()
    pg2.allow("DISK001", "photos")
    assert pg2.ok("DISK001", "photos/*") == True

    print("PASS: test_query_with_wildcards_conservative")


def test_exact_file_allow():
    """Test allowing a specific file."""
    pg = PathGuard()

    # Allow a specific file
    pg.allow("DISK001", "config/settings.json")

    # That specific file should be ok
    assert pg.ok("DISK001", "config/settings.json") == True

    # Other files in same directory should be denied
    assert pg.ok("DISK001", "config/secrets.json") == False

    print("PASS: test_exact_file_allow")


def test_multiple_disks():
    """Test that rules are disk-specific."""
    pg = PathGuard()

    # Allow on disk 1
    pg.allow("DISK001", "data")

    # Deny on disk 2 (but never allowed, so still denied)
    pg.deny("DISK002", "data")

    # Same path, different results per disk
    assert pg.ok("DISK001", "data/file.txt") == True
    assert pg.ok("DISK002", "data/file.txt") == False

    print("PASS: test_multiple_disks")


def test_trailing_slashes():
    """Test that trailing slashes are handled correctly."""
    pg = PathGuard()

    # Add with trailing slash
    pg.allow("DISK001", "photos/vacation/")

    # Should still match paths without trailing slash
    assert pg.ok("DISK001", "photos/vacation/pic.jpg") == True

    # Query with trailing slash should also work
    pg2 = PathGuard()
    pg2.allow("DISK001", "photos/vacation")
    # The path itself (as a directory reference) should be ok
    assert pg2.ok("DISK001", "photos/vacation") == True

    print("PASS: test_trailing_slashes")


def test_rule_order_matters():
    """Test that rules are evaluated in order, last match wins."""
    pg = PathGuard()

    # Order: allow -> deny -> allow
    pg.allow("DISK001", "data")
    pg.deny("DISK001", "data/restricted")
    pg.allow("DISK001", "data/restricted/public")

    assert pg.ok("DISK001", "data/file.txt") == True
    assert pg.ok("DISK001", "data/restricted/secret.txt") == False
    assert pg.ok("DISK001", "data/restricted/public/file.txt") == True

    print("PASS: test_rule_order_matters")


def test_nested_deny_within_allow():
    """Test deeply nested deny within allowed area."""
    pg = PathGuard()

    # Allow entire area
    pg.allow("DISK001", "projects")

    # Deny a deeply nested path
    pg.deny("DISK001", "projects/work/confidential/internal")

    # Most paths under projects should be allowed
    assert pg.ok("DISK001", "projects/work/file.txt") == True
    assert pg.ok("DISK001", "projects/work/confidential/file.txt") == True

    # But the specifically denied path should be blocked
    assert pg.ok("DISK001", "projects/work/confidential/internal/file.txt") == False

    print("PASS: test_nested_deny_within_allow")


def test_deny_only_has_no_effect():
    """Test that deny rules without prior allow have no effect (still denied)."""
    pg = PathGuard()

    # Only deny, no allow
    pg.deny("DISK001", "blocked")

    # Still denied because nothing was allowed
    assert pg.ok("DISK001", "blocked/file.txt") == False
    assert pg.ok("DISK001", "other/file.txt") == False

    print("PASS: test_deny_only_has_no_effect")


def run_all_tests():
    """Run all tests."""
    print("Running PathGuard tests...\n")

    test_default_deny()
    test_basic_allow()
    test_allow_with_backslashes()
    test_deny_exception()
    test_allow_within_deny()
    test_wildcard_single_star()
    test_wildcard_double_star()
    test_query_with_wildcards_conservative()
    test_exact_file_allow()
    test_multiple_disks()
    test_trailing_slashes()
    test_rule_order_matters()
    test_nested_deny_within_allow()
    test_deny_only_has_no_effect()

    print("\nAll tests passed!")


if __name__ == "__main__":
    run_all_tests()
