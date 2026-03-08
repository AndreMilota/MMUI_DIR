# scripts/app_2/test_query_feed_llm.py
"""
Tests for the query_feed_llm branch of the app_2 LangGraph workflow.

query_feed_llm handles file operations that require AI processing -
specifically renaming/restructuring tasks that are beyond what SQLite's
string functions can express (no regex, no pattern capture groups, etc.).

This file contains two sections:
  1. Basic routing test (from branching_agent_tests.py)
  2. SQL-incapable escalation tests (from sql_escalation_test.py)
     These verify that complex transforms correctly escalate FROM
     query_transform/query_copy TO query_feed_llm.

SQLite CAN do: REPLACE with fixed strings, SUBSTR with fixed positions,
               simple concatenation, UPPER/LOWER.
SQLite CANNOT do: regex replacement, variable-length prefix removal,
                  CamelCase conversion, pattern-based restructuring,
                  or context-dependent renaming decisions.
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
# Filesystem designed to expose the limits of SQLite string manipulation.
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

    fs.mkdir("C:/Projects/Archive")
    fs.cd("C:/Projects/Archive")
    fs.set_time("2026-01-15 00:00:00")
    fs.save("archive_report.txt", size_bytes=1024)
    fs.save("archive_summary.txt", size_bytes=2048)
    fs.save("archive_notes.txt", size_bytes=512)
    fs.save("old_data.csv", size_bytes=4096)
    fs.save("old_backup.csv", size_bytes=3072)

    fs.mkdir("C:/Music/Playlist")
    fs.cd("C:/Music/Playlist")
    fs.set_time("2026-01-20 00:00:00")
    fs.save("01_first_song.mp3", size_bytes=5000000)
    fs.save("02_second_song.mp3", size_bytes=5500000)
    fs.save("10_tenth_song.mp3", size_bytes=4800000)
    fs.save("123_numbered_track.mp3", size_bytes=5200000)

    fs.mkdir("C:/Code/Classes")
    fs.cd("C:/Code/Classes")
    fs.set_time("2026-02-01 00:00:00")
    fs.save("UserAccountManager.py", size_bytes=8192)
    fs.save("HttpRequestHandler.py", size_bytes=6144)
    fs.save("DataProcessingService.py", size_bytes=10240)

    fs.mkdir("C:/Documents/Duplicates")
    fs.cd("C:/Documents/Duplicates")
    fs.set_time("2026-02-05 00:00:00")
    fs.save("report.txt", size_bytes=1024)
    fs.save("report (1).txt", size_bytes=1024)
    fs.save("report (2).txt", size_bytes=1024)
    fs.save("budget (copy).txt", size_bytes=2048)
    fs.save("budget (another copy).txt", size_bytes=2048)

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
# Basic routing test - verify the branch is selected correctly.
# ===========================================================================

def test_query_feed_llm():
    """Test query_feed_llm branch - AI processing."""
    print("\n" + "="*70)
    print("TESTING: query_feed_llm (AI processing)")
    print("="*70)

    _, _, db_path = setup_test_filesystem("feed_llm")
    NOW = "2026-02-15 12:00:00"

    run_test(
        "AI rename files",
        "Use AI to suggest better names for my vacation photos based on their metadata",  # <-----------------------------------------
        db_path, NOW,
        expected_action="query_feed_llm"
    )


# ===========================================================================
# FROM: sql_escalation_test.py
# SQL-INCAPABLE escalation tests.
# These operations exceed SQLite's string capabilities and must escalate
# to query_feed_llm.
# ===========================================================================

def test_variable_numeric_prefix_removal():
    """
    Test: Remove numeric prefixes of varying lengths (01_, 02_, 123_, etc.)

    SQL CANNOT handle this: There's no regex in SQLite. You can't write
    a SQL expression that removes "any sequence of digits followed by underscore"
    because SUBSTR needs a fixed position and REPLACE needs a fixed string.

    Expected: query_feed_llm (needs LLM to generate the new names)
    """
    print("\n" + "="*70)
    print("TEST CATEGORY: SQL-INCAPABLE - Variable numeric prefix")
    print("="*70)

    _, _, db_path = setup_escalation_filesystem("numeric_prefix")
    NOW = "2026-02-15 12:00:00"

    run_test(
        "Remove track numbers from MP3 filenames",
        "Rename all MP3 files in C:/Music/Playlist by removing the leading track numbers (like 01_, 02_, 123_) from the beginning of each filename",  # <-----------------------------------------
        db_path, NOW,
        expected_action="query_feed_llm"
    )


def test_camelcase_to_snakecase():
    """
    Test: Convert CamelCase filenames to snake_case.

    SQL CANNOT handle this: Requires identifying uppercase letters
    within a string and inserting underscores before them. SQLite
    has no pattern-matching replacement capability.

    Expected: query_feed_llm (needs LLM or regex to do conversion)
    """
    print("\n" + "="*70)
    print("TEST CATEGORY: SQL-INCAPABLE - CamelCase to snake_case")
    print("="*70)

    _, _, db_path = setup_escalation_filesystem("camelcase")
    NOW = "2026-02-15 12:00:00"

    run_test(
        "Convert CamelCase to snake_case",
        "Rename all Python files in C:/Code/Classes by converting their CamelCase names to snake_case (e.g., UserAccountManager.py becomes user_account_manager.py)",  # <-----------------------------------------
        db_path, NOW,
        expected_action="query_feed_llm"
    )


def test_remove_copy_suffixes():
    """
    Test: Remove duplicate/copy suffixes like (1), (2), (copy), etc.

    SQL CANNOT handle this cleanly: The suffixes vary in content.
    While you could chain multiple REPLACE calls for known patterns,
    you can't handle arbitrary "(something)" suffixes without regex.

    Expected: query_feed_llm (needs pattern recognition)
    """
    print("\n" + "="*70)
    print("TEST CATEGORY: SQL-INCAPABLE - Copy suffix removal")
    print("="*70)

    _, _, db_path = setup_escalation_filesystem("copy_suffix")
    NOW = "2026-02-15 12:00:00"

    run_test(
        "Remove copy suffixes from duplicate files",
        "Rename files in C:/Documents/Duplicates by removing the copy indicators like (1), (2), (copy) from their names",  # <-----------------------------------------
        db_path, NOW,
        expected_action="query_feed_llm"
    )


def test_semantic_ai_renaming():
    """
    Test: Rename files based on their content/metadata semantics.

    SQL absolutely CANNOT handle this: Requires understanding file
    content, metadata context, and making intelligent naming decisions.

    Expected: query_feed_llm (explicitly needs AI processing)
    """
    print("\n" + "="*70)
    print("TEST CATEGORY: SQL-INCAPABLE - Semantic/AI renaming")
    print("="*70)

    _, _, db_path = setup_escalation_filesystem("semantic")
    NOW = "2026-02-15 12:00:00"

    run_test(
        "AI-based photo renaming",
        "Rename all the photos in C:/Photos/Vacation to have more descriptive names based on when they were taken and any available metadata",  # <-----------------------------------------
        db_path, NOW,
        expected_action="query_feed_llm"
    )


def test_pattern_based_extraction():
    """
    Test: Extract specific pattern from filename and restructure.

    SQL CANNOT handle this: Pattern extraction and restructuring
    requires regex capture groups or equivalent logic.

    Example: "IMG_0001.jpg" -> "vacation_photo_0001.jpg" (keeping the number)

    Expected: query_feed_llm (needs pattern extraction)
    """
    print("\n" + "="*70)
    print("TEST CATEGORY: SQL-INCAPABLE - Pattern extraction/restructure")
    print("="*70)

    _, _, db_path = setup_escalation_filesystem("pattern")
    NOW = "2026-02-15 12:00:00"

    run_test(
        "Restructure camera filenames keeping sequence numbers",
        "Rename photos in C:/Photos/Vacation by changing IMG_XXXX.jpg and DSC_XXXX.jpg to vacation_XXXX.jpg, keeping the original sequence numbers",  # <-----------------------------------------
        db_path, NOW,
        expected_action="query_feed_llm"
    )


def test_conditional_renaming():
    """
    Test: Rename files differently based on content of the filename.

    SQL has LIMITED capability here: CASE statements can handle some
    conditions, but complex conditional logic with string manipulation
    often exceeds what's practical in SQL.

    Expected: query_feed_llm (conditional logic too complex for SQL)
    """
    print("\n" + "="*70)
    print("TEST CATEGORY: SQL-INCAPABLE - Conditional renaming")
    print("="*70)

    _, _, db_path = setup_escalation_filesystem("conditional")
    NOW = "2026-02-15 12:00:00"

    run_test(
        "Conditional prefix based on file type",
        "Rename files in C:/Projects/Archive: if the filename starts with 'archive_', remove it; if it starts with 'old_', replace it with 'legacy_'; otherwise add 'misc_' prefix",  # <-----------------------------------------
        db_path, NOW,
        expected_action="query_feed_llm"
    )


def test_metadata_from_filename():
    """
    Test: Fix metadata from filename or vice versa.

    This is a semantic/AI task that requires understanding:
    - What metadata fields exist
    - How to extract information from filenames
    - How to generate corrections

    The SQL should retrieve the relevant files with their metadata and filenames,
    then the LLM will analyze and suggest fixes.

    Expected: query_feed_llm (requires semantic understanding)
    """
    print("\n" + "="*70)
    print("TEST CATEGORY: SQL-INCAPABLE - Metadata/filename reconciliation")
    print("="*70)

    _, _, db_path = setup_escalation_filesystem("metadata")
    NOW = "2026-02-15 12:00:00"

    result = run_test(
        "Fix metadata from filename",
        "In C:/Music/Playlist, see if you can fix the metadata from the file name and vice versa",  # <-----------------------------------------
        db_path, NOW,
        expected_action="query_feed_llm"
    )

    # Verify the SQL retrieves both filename and metadata columns
    sql = result.get('sql', '').lower()
    has_name = 'name' in sql or 'files.name' in sql
    has_metadata = any(col in sql for col in ['tag_artist', 'tag_title', 'tag_album', 'duration'])

    if has_name:
        print("SQL includes filename column: PASSED")
    else:
        print("WARNING: SQL may not include filename column")

    if has_metadata:
        print("SQL includes metadata columns: PASSED")
    else:
        print("WARNING: SQL may not include metadata columns")


def test_sql_incapable():
    """Run all SQL-incapable tests (should escalate to query_feed_llm)."""
    print("\n" + "#"*70)
    print("# RUNNING SQL-INCAPABLE TESTS")
    print("# These should escalate to query_feed_llm")
    print("#"*70)

    test_variable_numeric_prefix_removal()
    test_camelcase_to_snakecase()
    test_remove_copy_suffixes()
    test_semantic_ai_renaming()
    test_pattern_based_extraction()
    test_conditional_renaming()
    test_metadata_from_filename()


# ===========================================================================
# TEST RUNNER
# ===========================================================================

def test_all_feed_llm():
    """Run all query_feed_llm tests."""
    print("\n" + "#"*70)
    print("# RUNNING ALL query_feed_llm TESTS")
    print("#"*70)

    test_query_feed_llm()
    test_sql_incapable()

    print("\n" + "#"*70)
    print("# query_feed_llm TESTS COMPLETED")
    print("#"*70)


if __name__ == "__main__":
    test_all_feed_llm()
