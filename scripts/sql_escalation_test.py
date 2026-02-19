# scripts/sql_escalation_test.py
"""
Tests for SQL escalation logic in the branching LangGraph workflow.

These tests verify that the classifier correctly chooses between:
- query_transform/query_copy: When SQL can fully generate both source_path and dest_path
- query_feed_llm: When the transformation requires capabilities beyond SQLite's string functions

SQLite String Manipulation Capabilities:
- || (concatenation): Can construct paths from parts
- REPLACE(str, from, to): Can replace fixed substrings
- SUBSTR(str, start, length): Can extract/remove fixed-position characters
- INSTR(str, search): Can find position of fixed substring
- LTRIM/RTRIM/TRIM: Can remove whitespace or specific characters
- UPPER/LOWER: Case conversion (but not CamelCase manipulation)

SQLite String Manipulation LIMITATIONS (require LLM escalation):
- No regex replacement (can't do pattern-based substitutions)
- Can't handle variable-length prefixes (e.g., "remove leading digits")
- Can't do CamelCase to snake_case conversion
- Can't intelligently parse semantic patterns (e.g., "remove (copy)" suffixes with varying content)
- Can't make context-dependent decisions about renaming

Test Categories:
1. SQL-capable transformations (should route to query_transform/query_copy)
2. SQL-incapable transformations (should route to query_feed_llm)
"""
import os
from file_scan.fs_database import FSDatabase
from file_scan.fs_load import scan_path_into_db
from file_scan.mock_file_system.mock_files import MockFiles
from file_scan.mock_file_system.mock_fs_reader import MockFSReader
from app_2.runner import run_query


def make_test_filesystem(name: str = "escalation_test_fs") -> MockFiles:
    """Create a fresh mock filesystem for testing."""
    db_filename = f"{name}.sqlite"
    if os.path.exists(db_filename):
        os.unlink(db_filename)
    vfs = MockFiles(db_path=db_filename)
    vfs.set_time("2026-01-01 12:00:00")
    vfs.mount_volume(drive_letter='C')
    return vfs


def get_fresh_database(name: str = "escalation_test_db") -> FSDatabase:
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
    NOW = "2026-02-15 12:00:00"

    fs = make_test_filesystem(f"escalation_fs_{test_name}")

    # Directory for fixed-prefix tests (SQL CAN handle)
    fs.mkdir("C:/Projects/Archive")
    fs.mkdir("C:/Projects/Active")
    fs.cd("C:/Projects/Archive")
    fs.set_time("2026-01-15 00:00:00")
    # Files with fixed "archive_" prefix
    fs.save("archive_report.txt", size_bytes=1024)
    fs.save("archive_summary.txt", size_bytes=2048)
    fs.save("archive_notes.txt", size_bytes=512)
    # Files with fixed "old_" prefix
    fs.save("old_data.csv", size_bytes=4096)
    fs.save("old_backup.csv", size_bytes=3072)

    # Directory for numeric prefix tests (SQL CANNOT handle)
    fs.mkdir("C:/Music/Playlist")
    fs.cd("C:/Music/Playlist")
    fs.set_time("2026-01-20 00:00:00")
    # Variable-length numeric prefixes - SQL can't handle these with regex
    fs.save("01_first_song.mp3", size_bytes=5000000)
    fs.save("02_second_song.mp3", size_bytes=5500000)
    fs.save("10_tenth_song.mp3", size_bytes=4800000)
    fs.save("123_numbered_track.mp3", size_bytes=5200000)

    # Directory for CamelCase tests (SQL CANNOT handle)
    fs.mkdir("C:/Code/Classes")
    fs.cd("C:/Code/Classes")
    fs.set_time("2026-02-01 00:00:00")
    # CamelCase filenames that might need snake_case conversion
    fs.save("UserAccountManager.py", size_bytes=8192)
    fs.save("HttpRequestHandler.py", size_bytes=6144)
    fs.save("DataProcessingService.py", size_bytes=10240)

    # Directory for copy suffix tests (SQL CANNOT handle cleanly)
    fs.mkdir("C:/Documents/Duplicates")
    fs.cd("C:/Documents/Duplicates")
    fs.set_time("2026-02-05 00:00:00")
    # Files with various copy-style suffixes
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
    # Generic camera filenames that need intelligent renaming
    fs.save("IMG_0001.jpg", size_bytes=3000000)
    fs.save("IMG_0002.jpg", size_bytes=3200000)
    fs.save("DSC_1234.jpg", size_bytes=2800000)
    fs.save("DCIM0099.jpg", size_bytes=3100000)

    # Scan into database
    db = get_fresh_database(f"escalation_db_{test_name}")
    reader = MockFSReader(fs)
    scan_path_into_db(root_path="C:/", db=db, reader=reader)

    return fs, db, db.db_path


# =============================================================================
# Tests for SQL-CAPABLE transformations (should use query_transform/query_copy)
# =============================================================================

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


# =============================================================================
# Tests for SQL-INCAPABLE transformations (should escalate to query_feed_llm)
# =============================================================================

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
        "Rename all MP3 files in C:/Music/Playlist by removing the leading track numbers (like 01_, 02_, 123_) from the beginning of each filename",
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
        "Rename all Python files in C:/Code/Classes by converting their CamelCase names to snake_case (e.g., UserAccountManager.py becomes user_account_manager.py)",
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
        "Rename files in C:/Documents/Duplicates by removing the copy indicators like (1), (2), (copy) from their names",
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
        "Rename all the photos in C:/Photos/Vacation to have more descriptive names based on when they were taken and any available metadata",
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
        "Rename photos in C:/Photos/Vacation by changing IMG_XXXX.jpg and DSC_XXXX.jpg to vacation_XXXX.jpg, keeping the original sequence numbers",
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
        "Rename files in C:/Projects/Archive: if the filename starts with 'archive_', remove it; if it starts with 'old_', replace it with 'legacy_'; otherwise add 'misc_' prefix",
        db_path, NOW,
        expected_action="query_feed_llm"
    )


# =============================================================================
# Test Runners
# =============================================================================

def test_sql_capable():
    """Run all SQL-capable tests (should route to query_transform/query_copy)."""
    print("\n" + "#"*70)
    print("# RUNNING SQL-CAPABLE TESTS")
    print("# These should route to query_transform or query_copy")
    print("#"*70)

    test_simple_move_to_directory()
    test_delete_files()
    test_fixed_prefix_removal()
    test_simple_copy()


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


def test_all_escalation():
    """Run all escalation tests."""
    print("\n" + "#"*70)
    print("# RUNNING ALL SQL ESCALATION TESTS")
    print("#"*70)

    test_sql_capable()
    test_sql_incapable()

    print("\n" + "#"*70)
    print("# ALL ESCALATION TESTS COMPLETED")
    print("#"*70)


if __name__ == "__main__":
    test_all_escalation()
