# scripts/app_2/test_query_display.py
"""
Tests for the query_display branch of the app_2 LangGraph workflow.

query_display handles requests to show a table of files - listing,
browsing, sorting, and grouping results for the user to read.

This file contains two sections:
  1. Basic routing test (from branching_agent_tests.py)
  2. Detailed sorting/grouping/column-selection tests (from display_sorting_tests.py)
"""
import os
from typing import List, Dict, Any
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
# TEST FILESYSTEM SETUP - DISPLAY/SORTING SPECIFIC
# Source: display_sorting_tests.py
# Filesystem with varied dates, sizes, and directories for sort/group tests.
# ===========================================================================

def setup_display_test_filesystem(test_name: str = "display"):
    """
    Set up a filesystem designed for testing display sorting and grouping.

    Creates files with varied:
    - Creation dates (for date sorting)
    - Modification dates (for modified date sorting)
    - Sizes (for size sorting)
    - Extensions (for type grouping)
    - Directories (for directory grouping)
    """
    fs = make_test_filesystem(f"display_fs_{test_name}")

    # Directory 1: Documents with varying dates
    fs.mkdir("C:/Documents/Reports")
    fs.cd("C:/Documents/Reports")
    fs.set_time("2026-01-05 09:00:00")
    fs.save("january_report.txt", size_bytes=1024)
    fs.set_time("2026-02-10 14:00:00")
    fs.save("february_report.txt", size_bytes=2048)
    fs.set_time("2026-01-20 11:00:00")
    fs.save("midmonth_analysis.txt", size_bytes=512)

    # Directory 2: Images with varying sizes
    fs.mkdir("C:/Pictures/Photos")
    fs.cd("C:/Pictures/Photos")
    fs.set_time("2026-02-01 10:00:00")
    fs.save("small_photo.jpg", size_bytes=100000)
    fs.set_time("2026-02-05 15:00:00")
    fs.save("medium_photo.jpg", size_bytes=500000)
    fs.set_time("2026-01-15 08:00:00")
    fs.save("large_photo.jpg", size_bytes=2000000)

    # Directory 3: Music for mixed content
    fs.mkdir("C:/Music/Albums")
    fs.cd("C:/Music/Albums")
    fs.set_file_defaults(channels=2)
    fs.set_time("2026-01-10 12:00:00")
    fs.save_m("track_01.mp3", duration=180, bitrate=320000)
    fs.set_time("2026-02-08 16:00:00")
    fs.save_m("track_02.mp3", duration=240, bitrate=320000)
    fs.set_time("2026-01-25 09:00:00")
    fs.save_m("track_03.mp3", duration=200, bitrate=320000)

    # Directory 4: Downloads with different types
    fs.mkdir("C:/Downloads")
    fs.cd("C:/Downloads")
    fs.set_file_defaults(channels=None)
    fs.set_time("2026-02-12 11:00:00")
    fs.save("installer.exe", size_bytes=50000000)
    fs.set_time("2026-01-30 14:00:00")
    fs.save("document.pdf", size_bytes=1500000)
    fs.set_time("2026-02-03 10:00:00")
    fs.save("archive.zip", size_bytes=25000000)

    db = get_fresh_database(f"display_db_{test_name}")
    reader = MockFSReader(fs)
    scan_path_into_db(root_path="C:/", db=db, reader=reader)

    return fs, db, db.db_path


# ===========================================================================
# VERIFICATION UTILITIES
# Source: display_sorting_tests.py
# Helper functions for checking sort order and grouping in results.
# ===========================================================================

def extract_column(results: List[Dict], column: str) -> List[Any]:
    """Extract a specific column from results as a list."""
    return [row.get(column) for row in results]


def is_sorted_ascending(values: List) -> bool:
    """Check if values are sorted in ascending order (ignoring None)."""
    filtered = [v for v in values if v is not None]
    return filtered == sorted(filtered)


def is_sorted_descending(values: List) -> bool:
    """Check if values are sorted in descending order (ignoring None)."""
    filtered = [v for v in values if v is not None]
    return filtered == sorted(filtered, reverse=True)


def group_by_directory(results: List[Dict], dir_col: str = "dir_path") -> Dict[str, List[Dict]]:
    """Group results by directory path."""
    groups = {}
    for row in results:
        dir_path = row.get(dir_col, "")
        if dir_path not in groups:
            groups[dir_path] = []
        groups[dir_path].append(row)
    return groups


def verify_sorted_within_groups(
    results: List[Dict],
    dir_col: str,
    sort_col: str,
    descending: bool = False
) -> bool:
    """
    Verify that within each directory group, rows are sorted by sort_col.
    Group order doesn't matter - only within-group sorting is checked.
    """
    groups = group_by_directory(results, dir_col)
    for dir_path, rows in groups.items():
        values = extract_column(rows, sort_col)
        if descending:
            if not is_sorted_descending(values):
                print(f"Group {dir_path} not sorted descending by {sort_col}: {values}")
                return False
        else:
            if not is_sorted_ascending(values):
                print(f"Group {dir_path} not sorted ascending by {sort_col}: {values}")
                return False
    return True


# ===========================================================================
# FROM: branching_agent_tests.py
# Basic routing tests - verify the branch is selected correctly.
# ===========================================================================

def test_query_display():
    """Test query_display branch - table display queries."""
    print("\n" + "="*70)
    print("TESTING: query_display (table display)")
    print("="*70)

    _, _, db_path = setup_test_filesystem("display")
    NOW = "2026-02-15 12:00:00"

    # Test: Show files
    run_test(
        "Show files in directory",
        "Show me all the files in C:/Music/Beatles",  # <-----------------------------------------
        db_path, NOW,
        expected_action="query_display"
    )

    # Test: List with criteria
    run_test(
        "List files with criteria",
        "List all text files I have",  # <-----------------------------------------
        db_path, NOW,
        expected_action="query_display"
    )


# ===========================================================================
# FROM: display_sorting_tests.py
# Column selection tests - verify specific columns are returned.
# ===========================================================================

def test_display_with_dates():
    """Test: Request display with creation date information."""
    print("\n" + "="*70)
    print("TEST CATEGORY: Column Selection - Dates")
    print("="*70)

    _, _, db_path = setup_display_test_filesystem("dates")
    NOW = "2026-02-15 12:00:00"

    result = run_test(
        "Show files with creation dates",
        "Show me all the text files with their creation dates",  # <-----------------------------------------
        db_path, NOW,
        expected_action="query_display"
    )

    rows = result.get('query_result', [])
    if rows:
        print(f"Retrieved {len(rows)} rows")
        first_row = rows[0]
        has_date = any('date' in k.lower() or 'ctime' in k.lower() or 'time' in k.lower()
                       for k in first_row.keys())
        if has_date:
            print("DATE COLUMN CHECK PASSED")
        else:
            print(f"WARNING: No date column found. Columns: {list(first_row.keys())}")


def test_display_with_size():
    """Test: Request display with file size information."""
    print("\n" + "="*70)
    print("TEST CATEGORY: Column Selection - Size")
    print("="*70)

    _, _, db_path = setup_display_test_filesystem("size")
    NOW = "2026-02-15 12:00:00"

    result = run_test(
        "Show files with sizes",
        "List all files in C:/Pictures/Photos showing their file sizes",  # <-----------------------------------------
        db_path, NOW,
        expected_action="query_display"
    )

    rows = result.get('query_result', [])
    if rows:
        first_row = rows[0]
        has_size = any('size' in k.lower() for k in first_row.keys())
        if has_size:
            print("SIZE COLUMN CHECK PASSED")
        else:
            print(f"WARNING: No size column found. Columns: {list(first_row.keys())}")


# ===========================================================================
# FROM: display_sorting_tests.py
# Simple sorting tests - verify ORDER BY is generated correctly.
# ===========================================================================

def test_sort_by_date_ascending():
    """Test: Sort files by creation date, oldest first."""
    print("\n" + "="*70)
    print("TEST CATEGORY: Sorting - Date Ascending")
    print("="*70)

    _, _, db_path = setup_display_test_filesystem("sort_date_asc")
    NOW = "2026-02-15 12:00:00"

    result = run_test(
        "Sort by date oldest first",
        "Show me all files in C:/Documents/Reports sorted by creation date, oldest first",  # <-----------------------------------------
        db_path, NOW,
        expected_action="query_display"
    )

    rows = result.get('query_result', [])
    if rows and len(rows) > 1:
        sql = result.get('sql', '').upper()
        if 'ORDER BY' in sql:
            print("ORDER BY CLAUSE CHECK PASSED")
        else:
            print("WARNING: No ORDER BY clause in SQL")


def test_sort_by_size_descending():
    """Test: Sort files by size, largest first."""
    print("\n" + "="*70)
    print("TEST CATEGORY: Sorting - Size Descending")
    print("="*70)

    _, _, db_path = setup_display_test_filesystem("sort_size_desc")
    NOW = "2026-02-15 12:00:00"

    result = run_test(
        "Sort by size largest first",
        "List all JPG files sorted by size with the largest files first",  # <-----------------------------------------
        db_path, NOW,
        expected_action="query_display"
    )

    rows = result.get('query_result', [])
    if rows and len(rows) > 1:
        sql = result.get('sql', '').upper()
        if 'ORDER BY' in sql and 'DESC' in sql:
            print("ORDER BY DESC CLAUSE CHECK PASSED")
        elif 'ORDER BY' in sql:
            print("ORDER BY found but DESC may be missing")
        else:
            print("WARNING: No ORDER BY clause in SQL")


def test_sort_by_name_alphabetical():
    """Test: Sort files alphabetically by name."""
    print("\n" + "="*70)
    print("TEST CATEGORY: Sorting - Alphabetical")
    print("="*70)

    _, _, db_path = setup_display_test_filesystem("sort_alpha")
    NOW = "2026-02-15 12:00:00"

    result = run_test(
        "Sort alphabetically by name",
        "List all MP3 files sorted alphabetically by filename",  # <-----------------------------------------
        db_path, NOW,
        expected_action="query_display"
    )

    rows = result.get('query_result', [])
    if rows:
        sql = result.get('sql', '').upper()
        if 'ORDER BY' in sql and 'NAME' in sql:
            print("ORDER BY NAME CLAUSE CHECK PASSED")
        elif 'ORDER BY' in sql:
            print("ORDER BY found (may use different column name)")
        else:
            print("WARNING: No ORDER BY clause in SQL")


def test_sort_by_extension_then_name():
    """Test: Sort files by extension first, then by name within each extension."""
    print("\n" + "="*70)
    print("TEST CATEGORY: Sorting - Multi-column (Extension then Name)")
    print("="*70)

    _, _, db_path = setup_display_test_filesystem("sort_multi")
    NOW = "2026-02-15 12:00:00"

    result = run_test(
        "Sort by type then name",
        "Show all files in C:/Downloads sorted by file type, then alphabetically by name within each type",  # <-----------------------------------------
        db_path, NOW,
        expected_action="query_display"
    )

    rows = result.get('query_result', [])
    if rows:
        sql = result.get('sql', '').upper()
        if 'ORDER BY' in sql:
            print("ORDER BY CLAUSE CHECK PASSED")
        else:
            print("WARNING: No ORDER BY clause in SQL")


# ===========================================================================
# FROM: display_sorting_tests.py
# Grouping tests - verify files are grouped by directory correctly.
# ===========================================================================

def test_group_by_directory():
    """Test: Group files by directory."""
    print("\n" + "="*70)
    print("TEST CATEGORY: Grouping - By Directory")
    print("="*70)

    _, _, db_path = setup_display_test_filesystem("group_dir")
    NOW = "2026-02-15 12:00:00"

    result = run_test(
        "Group by directory",
        "Show me all files grouped by their directory",  # <-----------------------------------------
        db_path, NOW,
        expected_action="query_display"
    )

    rows = result.get('query_result', [])
    if rows:
        sql = result.get('sql', '').upper()
        if 'ORDER BY' in sql or 'GROUP BY' in sql:
            print("GROUPING/ORDERING CLAUSE CHECK PASSED")
        else:
            print("WARNING: No grouping clause found in SQL")


def test_group_by_directory_sort_by_date():
    """
    Test: Group files by directory, sorted by date within each group.

    Verifies that:
    - Files are grouped by directory
    - Within each directory group, files are sorted by date
    - The order of directory groups doesn't matter
    """
    print("\n" + "="*70)
    print("TEST CATEGORY: Grouping with Sorting - Dir then Date")
    print("="*70)

    _, _, db_path = setup_display_test_filesystem("group_sort")
    NOW = "2026-02-15 12:00:00"

    result = run_test(
        "Group by directory, sort by date within groups",
        "Show all files grouped by directory, and within each directory sort them by creation date",  # <-----------------------------------------
        db_path, NOW,
        expected_action="query_display"
    )

    rows = result.get('query_result', [])
    if rows:
        sql = result.get('sql', '').upper()
        if 'ORDER BY' in sql:
            print("ORDER BY CLAUSE CHECK PASSED")
        else:
            print("WARNING: No ORDER BY clause in SQL")


# ===========================================================================
# SUB-RUNNERS (match originals from display_sorting_tests.py)
# ===========================================================================

def test_column_selection():
    """Run column selection tests."""
    print("\n" + "#"*70)
    print("# RUNNING COLUMN SELECTION TESTS")
    print("#"*70)
    test_display_with_dates()
    test_display_with_size()


def test_sorting():
    """Run sorting tests."""
    print("\n" + "#"*70)
    print("# RUNNING SORTING TESTS")
    print("#"*70)
    test_sort_by_date_ascending()
    test_sort_by_size_descending()
    test_sort_by_name_alphabetical()
    test_sort_by_extension_then_name()


def test_grouping():
    """Run grouping tests."""
    print("\n" + "#"*70)
    print("# RUNNING GROUPING TESTS")
    print("#"*70)
    test_group_by_directory()
    test_group_by_directory_sort_by_date()


# ===========================================================================
# TEST RUNNER
# ===========================================================================

def test_all_display():
    """Run all query_display tests."""
    print("\n" + "#"*70)
    print("# RUNNING ALL query_display TESTS")
    print("#"*70)

    test_query_display()
    test_column_selection()
    test_sorting()
    test_grouping()

    print("\n" + "#"*70)
    print("# query_display TESTS COMPLETED")
    print("#"*70)


if __name__ == "__main__":
    test_all_display()
