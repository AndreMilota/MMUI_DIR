# scripts/app_2/test_query_transform.py
"""
Tests for the query_transform branch of the app_2 LangGraph workflow.

query_transform handles file move, rename, and delete operations where
SQL can fully generate both the source and destination paths.

This file contains two sections:
  1. Basic routing test (from branching_agent_tests.py)
  2. SQL-capable transform tests (from sql_escalation_test.py)
     These verify that simple transforms stay in query_transform and
     do NOT escalate to query_feed_llm.
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
# Filesystem with fixed prefixes, numeric prefixes, CamelCase names, etc.
# Used by the SQL-capable tests below.
# ===========================================================================

def setup_escalation_filesystem(test_name: str = "escalation"):
    """
    Set up a filesystem specifically designed to test SQL escalation scenarios.

    Includes files with:
    - Fixed prefixes (SQL can handle: REPLACE)
    - Numeric prefixes of varying length (SQL cannot handle: needs regex)
    - CamelCase names (SQL cannot handle: needs pattern recognition)
    - Copy suffixes like (1), (2), (copy) (SQL cannot handle cleanly)
    - Files needing semantic/AI-based renaming
    """
    fs = make_test_filesystem(f"escalation_fs_{test_name}")

    # Directory for fixed-prefix tests (SQL CAN handle)
    fs.mkdir("C:/Projects/Archive")
    fs.mkdir("C:/Projects/Active")
    fs.cd("C:/Projects/Archive")
    fs.set_time("2026-01-15 00:00:00")
    fs.save("archive_report.txt", size_bytes=1024)
    fs.save("archive_summary.txt", size_bytes=2048)
    fs.save("archive_notes.txt", size_bytes=512)
    fs.save("old_data.csv", size_bytes=4096)
    fs.save("old_backup.csv", size_bytes=3072)

    # Directory for numeric prefix tests (SQL CANNOT handle)
    fs.mkdir("C:/Music/Playlist")
    fs.cd("C:/Music/Playlist")
    fs.set_time("2026-01-20 00:00:00")
    fs.save("01_first_song.mp3", size_bytes=5000000)
    fs.save("02_second_song.mp3", size_bytes=5500000)
    fs.save("10_tenth_song.mp3", size_bytes=4800000)
    fs.save("123_numbered_track.mp3", size_bytes=5200000)

    # Directory for CamelCase tests (SQL CANNOT handle)
    fs.mkdir("C:/Code/Classes")
    fs.cd("C:/Code/Classes")
    fs.set_time("2026-02-01 00:00:00")
    fs.save("UserAccountManager.py", size_bytes=8192)
    fs.save("HttpRequestHandler.py", size_bytes=6144)
    fs.save("DataProcessingService.py", size_bytes=10240)

    # Directory for copy suffix tests (SQL CANNOT handle cleanly)
    fs.mkdir("C:/Documents/Duplicates")
    fs.cd("C:/Documents/Duplicates")
    fs.set_time("2026-02-05 00:00:00")
    fs.save("report.txt", size_bytes=1024)
    fs.save("report (1).txt", size_bytes=1024)
    fs.save("report (2).txt", size_bytes=1024)
    fs.save("budget (copy).txt", size_bytes=2048)
    fs.save("budget (another copy).txt", size_bytes=2048)

    # Directory for simple move/copy tests (SQL CAN handle)
    fs.mkdir("C:/Downloads/Unsorted")
    fs.mkdir("C:/Downloads/Sorted")
    fs.cd("C:/Downloads/Unsorted")
    fs.set_time("2026-02-10 00:00:00")
    fs.save("file1.pdf", size_bytes=102400)
    fs.save("file2.pdf", size_bytes=204800)
    fs.save("image.jpg", size_bytes=1024000)

    # Directory for semantic/AI renaming (absolutely needs LLM)
    fs.mkdir("C:/Photos/Vacation")
    fs.cd("C:/Photos/Vacation")
    fs.set_time("2026-02-12 00:00:00")
    fs.save("IMG_0001.jpg", size_bytes=3000000)
    fs.save("IMG_0002.jpg", size_bytes=3200000)
    fs.save("DSC_1234.jpg", size_bytes=2800000)
    fs.save("DCIM0099.jpg", size_bytes=3100000)

    db = get_fresh_database(f"escalation_db_{test_name}")
    reader = MockFSReader(fs)
    scan_path_into_db(root_path="C:/", db=db, reader=reader)

    return fs, db, db.db_path


# ===========================================================================
# FROM: branching_agent_tests.py
# Basic routing tests - verify the branch is selected correctly.
# ===========================================================================

def test_query_transform():
    """Test query_transform branch - file move/rename/delete."""
    print("\n" + "="*70)
    print("TESTING: query_transform (move/rename/delete)")
    print("="*70)

    _, _, db_path = setup_test_filesystem("transform")
    NOW = "2026-02-15 12:00:00"

    # Test: Delete files
    run_test(
        "Delete temp files",
        "Delete all the .tmp files in C:/Downloads/Temp",
        db_path, NOW,
        expected_action="query_transform"
    )

    # Test: Move files
    run_test(
        "Move files",
        "Move all files from C:/Downloads/Temp to C:/Archive",
        db_path, NOW,
        expected_action="query_transform"
    )


# ===========================================================================
# FROM: sql_escalation_test.py
# SQL-CAPABLE transform tests.
# These operations can be expressed in pure SQL and should NOT escalate
# to query_feed_llm - they stay in query_transform.
# ===========================================================================

def test_simple_move_to_directory():
    """
    Test: Move all files from one directory to another.

    SQL CAN handle this: Simply construct dest_path by replacing the
    directory portion of the path. Uses basic string concatenation.

    Expected: query_transform (pure SQL can generate both columns)
    """
    print("\n" + "="*70)
    print("TEST CATEGORY: SQL-CAPABLE - Simple directory move")
    print("="*70)

    _, _, db_path = setup_escalation_filesystem("simple_move")
    NOW = "2026-02-15 12:00:00"

    run_test(
        "Move PDFs to another directory",
        "Move all PDF files from C:/Downloads/Unsorted to C:/Downloads/Sorted",
        db_path, NOW,
        expected_action="query_transform"
    )


def test_delete_files():
    """
    Test: Delete files matching criteria.

    SQL CAN handle this: dest_path is simply NULL for deletions.

    Expected: query_transform (pure SQL can generate both columns)
    """
    print("\n" + "="*70)
    print("TEST CATEGORY: SQL-CAPABLE - Delete files")
    print("="*70)

    _, _, db_path = setup_escalation_filesystem("delete")
    NOW = "2026-02-15 12:00:00"

    run_test(
        "Delete old archive files",
        "Delete all the .txt files in C:/Projects/Archive",
        db_path, NOW,
        expected_action="query_transform"
    )


def test_fixed_prefix_removal():
    """
    Test: Remove a fixed, known prefix from filenames.

    SQL CAN handle this: REPLACE(name, 'archive_', '') works perfectly
    for fixed string prefixes.

    Expected: query_transform (REPLACE function can do this)
    """
    print("\n" + "="*70)
    print("TEST CATEGORY: SQL-CAPABLE - Fixed prefix removal")
    print("="*70)

    _, _, db_path = setup_escalation_filesystem("fixed_prefix")
    NOW = "2026-02-15 12:00:00"

    run_test(
        "Remove 'archive_' prefix from filenames",
        "Rename all files in C:/Projects/Archive by removing the 'archive_' prefix from their names",
        db_path, NOW,
        expected_action="query_transform"
    )


def test_sql_capable():
    """Run all SQL-capable transform tests (should route to query_transform)."""
    print("\n" + "#"*70)
    print("# RUNNING SQL-CAPABLE TRANSFORM TESTS")
    print("# These should route to query_transform, not query_feed_llm")
    print("#"*70)

    test_simple_move_to_directory()
    test_delete_files()
    test_fixed_prefix_removal()


# ===========================================================================
# TEST RUNNER
# ===========================================================================

def test_all_transform():
    """Run all query_transform tests."""
    print("\n" + "#"*70)
    print("# RUNNING ALL query_transform TESTS")
    print("#"*70)

    test_query_transform()
    test_sql_capable()

    print("\n" + "#"*70)
    print("# query_transform TESTS COMPLETED")
    print("#"*70)


if __name__ == "__main__":
    test_all_transform()
