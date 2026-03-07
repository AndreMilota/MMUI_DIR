# scripts/app_2/test_query_copy.py
"""
Tests for the query_copy branch of the app_2 LangGraph workflow.

query_copy handles file copy operations where SQL can fully generate
both the source and destination paths. Unlike query_transform, the
original files are kept in place.

This file contains two sections:
  1. Basic routing test (from branching_agent_tests.py)
  2. SQL-capable copy test (from sql_escalation_test.py)
"""
import os
from file_scan.fs_database import FSDatabase
from file_scan.fs_load import scan_path_into_db
from file_scan.mock_file_system.mock_files import MockFiles
from file_scan.mock_file_system.mock_fs_reader import MockFSReader
from app_2.runner import run_query


# ===========================================================================
# SHARED TEST INFRASTRUCTURE
# Duplicated in each branch test file so each file runs standalone.
# Original source: branching_agent_tests.py
# ===========================================================================

def make_test_filesystem(name: str = "test_fs") -> MockFiles:
    """Create a fresh mock filesystem for testing."""
    db_filename = f"{name}.sqlite"
    if os.path.exists(db_filename):
        os.unlink(db_filename)
    vfs = MockFiles(db_path=db_filename)
    vfs.set_time("2026-01-01 12:00:00")
    vfs.mount_volume(drive_letter='C')
    return vfs


def get_fresh_database(name: str = "test_db") -> FSDatabase:
    """Create a fresh database for testing."""
    db_path = f"{name}.sqlite"
    if os.path.exists(db_path):
        os.unlink(db_path)
    db = FSDatabase(db_path)
    return db


def run_test(label: str, query: str, db_path: str, now: str, expected_action: str = None):
    """Run a test query and print results."""
    print(f"\n{'='*70}")
    print(f"TEST: {label}")
    print(f"QUERY: {query}")
    print(f"EXPECTED ACTION: {expected_action or 'any'}")
    print(f"{'='*70}")

    result = run_query(query, now=now, db_path=db_path)

    print(f"\nACTION TYPE: {result['action_type']}")
    print(f"REASONING: {result['reasoning']}")
    if result.get('sql'):
        print(f"SQL:\n{result['sql']}")
    if result.get('query_error'):
        print(f"ERROR: {result['query_error']}")
    print(f"RESPONSE: {result['final_response']}")
    print(f"{'='*70}\n")

    if expected_action:
        assert result['action_type'] == expected_action, \
            f"Expected action '{expected_action}', got '{result['action_type']}'"
        print(f"ACTION TYPE CHECK PASSED")

    return result


# ===========================================================================
# TEST FILESYSTEM SETUP - GENERAL
# Source: branching_agent_tests.py
# Rich mock filesystem with music, documents, and pictures.
# Used by the basic routing test below.
# ===========================================================================

def setup_test_filesystem(test_name: str = "default"):
    """
    Set up a realistic test filesystem with various file types.
    Returns (mock_fs, database, db_path)
    """
    fs = make_test_filesystem(f"branching_fs_{test_name}")

    fs.mkdir("C:/Documents/Reports")
    fs.mkdir("C:/Documents/Letters")
    fs.mkdir("C:/Music/Beatles")
    fs.mkdir("C:/Music/Rock")
    fs.mkdir("C:/Pictures/Vacation")
    fs.mkdir("C:/Downloads/Temp")

    fs.cd("C:/Documents/Reports")
    fs.set_time("2026-01-10 00:00:00")
    fs.save("quarterly_report.txt", size_bytes=2048)
    fs.save("annual_summary.txt", size_bytes=4096)
    fs.set_time("2026-02-10 00:00:00")
    fs.save("meeting_notes.txt", size_bytes=512)

    fs.cd("C:/Documents/Letters")
    fs.set_time("2026-02-01 00:00:00")
    fs.save("cover_letter.txt", size_bytes=300)
    fs.save("thank_you.txt", size_bytes=400)

    fs.cd("C:/Music/Beatles")
    fs.set_file_defaults(tag_artist="The Beatles", channels=2)
    fs.set_time("2026-01-05 00:00:00")
    fs.save_m("yesterday.mp3", duration=180, bitrate=320000)
    fs.save_m("let_it_be.mp3", duration=240, bitrate=320000)
    fs.set_time("2026-01-20 00:00:00")
    fs.save_m("hey_jude.mp3", duration=430, bitrate=320000)

    fs.cd("C:/Music/Rock")
    fs.set_file_defaults(tag_artist=None, channels=2)
    fs.set_time("2026-02-03 00:00:00")
    fs.save_m("bohemian_rhapsody.mp3", duration=354, bitrate=320000, tag_artist="Queen")
    fs.save_m("stairway_to_heaven.mp3", duration=482, bitrate=320000, tag_artist="Led Zeppelin")
    fs.save_m("Yellow Submarine.mp3", duration=482, bitrate=320000, tag_artist="The Beatles")

    fs.mkdir("C:/Music/HighRes")
    fs.cd("C:/Music/HighRes")
    fs.set_time("2026-02-05 00:00:00")
    fs.save_m("classical_piece.wav", duration=300, bitrate=1411000, tag_artist="Mozart")
    fs.save_m("jazz_track.aiff", duration=240, bitrate=1411000, tag_artist="Miles Davis")

    fs.cd("C:/Pictures/Vacation")
    fs.set_file_defaults(tag_artist=None, channels=None)
    fs.set_time("2026-01-15 00:00:00")
    fs.save("beach_sunset.jpg", size_bytes=2500000)
    fs.save("mountain_view.jpg", size_bytes=3200000)
    fs.save("family_photo.jpg", size_bytes=1800000)

    fs.cd("C:/Downloads/Temp")
    fs.set_time("2025-12-01 00:00:00")
    fs.save("old_installer.exe", size_bytes=50000000)
    fs.save("temp_data.tmp", size_bytes=1024)
    fs.save("cache_file.tmp", size_bytes=2048)

    db = get_fresh_database(f"branching_db_{test_name}")
    reader = MockFSReader(fs)
    scan_path_into_db(root_path="C:/", db=db, reader=reader)

    return fs, db, db.db_path


# ===========================================================================
# TEST FILESYSTEM SETUP - ESCALATION SCENARIOS
# Source: sql_escalation_test.py
# Filesystem with simple copy targets.
# Used by the SQL-capable copy test below.
# ===========================================================================

def setup_escalation_filesystem(test_name: str = "escalation"):
    """
    Set up a filesystem for testing SQL escalation scenarios.
    Returns (mock_fs, database, db_path)
    """
    fs = make_test_filesystem(f"escalation_fs_{test_name}")

    fs.mkdir("C:/Projects/Archive")
    fs.cd("C:/Projects/Archive")
    fs.set_time("2026-01-15 00:00:00")
    fs.save("archive_report.txt", size_bytes=1024)
    fs.save("archive_summary.txt", size_bytes=2048)
    fs.save("archive_notes.txt", size_bytes=512)
    fs.save("old_data.csv", size_bytes=4096)
    fs.save("old_backup.csv", size_bytes=3072)

    fs.mkdir("C:/Downloads/Unsorted")
    fs.mkdir("C:/Downloads/Sorted")
    fs.cd("C:/Downloads/Unsorted")
    fs.set_time("2026-02-10 00:00:00")
    fs.save("file1.pdf", size_bytes=102400)
    fs.save("file2.pdf", size_bytes=204800)
    fs.save("image.jpg", size_bytes=1024000)

    db = get_fresh_database(f"escalation_db_{test_name}")
    reader = MockFSReader(fs)
    scan_path_into_db(root_path="C:/", db=db, reader=reader)

    return fs, db, db.db_path


# ===========================================================================
# FROM: branching_agent_tests.py
# Basic routing test - verify the branch is selected correctly.
# ===========================================================================

def test_query_copy():
    """Test query_copy branch - file copy operations."""
    print("\n" + "="*70)
    print("TESTING: query_copy (copy operations)")
    print("="*70)

    _, _, db_path = setup_test_filesystem("copy")
    NOW = "2026-02-15 12:00:00"

    run_test(
        "Copy files",
        "Copy all jpg files from C:/Pictures/Vacation to C:/Backup/Photos",
        db_path, NOW,
        expected_action="query_copy"
    )


# ===========================================================================
# FROM: sql_escalation_test.py
# SQL-CAPABLE copy test.
# This operation can be expressed in pure SQL and should NOT escalate
# to query_feed_llm - it stays in query_copy.
# ===========================================================================

def test_simple_copy():
    """
    Test: Copy files to a new directory.

    SQL CAN handle this: Same as move, just construct new dest_path.

    Expected: query_copy (pure SQL can generate both columns)
    """
    print("\n" + "="*70)
    print("TEST CATEGORY: SQL-CAPABLE - Simple copy")
    print("="*70)

    _, _, db_path = setup_escalation_filesystem("simple_copy")
    NOW = "2026-02-15 12:00:00"

    run_test(
        "Copy JPGs to backup",
        "Copy all JPG files from C:/Downloads/Unsorted to C:/Backup/Images",
        db_path, NOW,
        expected_action="query_copy"
    )


# ===========================================================================
# TEST RUNNER
# ===========================================================================

def test_all_copy():
    """Run all query_copy tests."""
    print("\n" + "#"*70)
    print("# RUNNING ALL query_copy TESTS")
    print("#"*70)

    test_query_copy()
    test_simple_copy()

    print("\n" + "#"*70)
    print("# query_copy TESTS COMPLETED")
    print("#"*70)


if __name__ == "__main__":
    test_all_copy()
