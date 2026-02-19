# scripts/branching_agent_tests.py
"""
Tests for the branching LangGraph workflow in app_2.

Tests each action type/branch:
- query_respond: Single value queries synthesized to natural language
- query_display: Table display queries
- query_store: Multi-turn dialog table storage
- query_transform: File move/rename/delete operations
- query_copy: File copy operations
- query_feed_llm: AI processing of files
- query_external: External app invocation
- web_search: Web research queries
- direct_answer: Conversational queries
"""
import os
from file_scan.fs_database import FSDatabase
from file_scan.fs_load import scan_path_into_db
from file_scan.mock_file_system.mock_files import MockFiles
from file_scan.mock_file_system.mock_fs_reader import MockFSReader
from app_2.runner import run_query


def make_test_filesystem(name: str = "branching_test_fs") -> MockFiles:
    """Create a fresh mock filesystem for testing."""
    db_filename = f"{name}.sqlite"
    if os.path.exists(db_filename):
        os.unlink(db_filename)
    vfs = MockFiles(db_path=db_filename)
    vfs.set_time("2026-01-01 12:00:00")
    vfs.mount_volume(drive_letter='C')
    return vfs


def get_fresh_database(name: str = "branching_test_db") -> FSDatabase:
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
Total_length_of_Beatles_files = 0
def setup_test_filesystem(test_name: str = "default"):
    """
    Set up a realistic test filesystem with various file types.
    Returns (mock_fs, database, db_path)
    """
    NOW = "2026-02-15 12:00:00"

    fs = make_test_filesystem(f"branching_fs_{test_name}")

    # Create directory structure
    fs.mkdir("C:/Documents/Reports")
    fs.mkdir("C:/Documents/Letters")
    fs.mkdir("C:/Music/Beatles")
    fs.mkdir("C:/Music/Rock")
    fs.mkdir("C:/Pictures/Vacation")
    fs.mkdir("C:/Downloads/Temp")

    # Documents
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

    # Music - Beatles
    fs.cd("C:/Music/Beatles")
    fs.set_file_defaults(tag_artist="The Beatles", channels=2)
    fs.set_time("2026-01-05 00:00:00")
    fs.save_m("yesterday.mp3", duration=180, bitrate=320000)
    fs.save_m("let_it_be.mp3", duration=240, bitrate=320000)
    fs.set_time("2026-01-20 00:00:00")
    fs.save_m("hey_jude.mp3", duration=430, bitrate=320000)

    # Music - Rock
    fs.cd("C:/Music/Rock")
    fs.set_file_defaults(tag_artist=None, channels=2)
    fs.set_time("2026-02-03 00:00:00")
    fs.save_m("bohemian_rhapsody.mp3", duration=354, bitrate=320000, tag_artist="Queen")
    fs.save_m("stairway_to_heaven.mp3", duration=482, bitrate=320000, tag_artist="Led Zeppelin")
    fs.save_m("Yellow Submarine.mp3", duration=482, bitrate=320000, tag_artist="The Beatles")  # Same artist but different folder

    Total_length_of_Beatles_files = 180 + 240 + 430 + 482  # Sum of durations of Beatles files for testing aggregate queries
    # Pictures
    fs.cd("C:/Pictures/Vacation")
    fs.set_file_defaults(tag_artist=None, channels=None)
    fs.set_time("2026-01-15 00:00:00")
    fs.save("beach_sunset.jpg", size_bytes=2500000)
    fs.save("mountain_view.jpg", size_bytes=3200000)
    fs.save("family_photo.jpg", size_bytes=1800000)

    # Downloads/Temp - files to potentially delete
    fs.cd("C:/Downloads/Temp")
    fs.set_time("2025-12-01 00:00:00")  # Old files
    fs.save("old_installer.exe", size_bytes=50000000)
    fs.save("temp_data.tmp", size_bytes=1024)
    fs.save("cache_file.tmp", size_bytes=2048)

    # Scan into database
    db = get_fresh_database(f"branching_db_{test_name}")
    reader = MockFSReader(fs)
    scan_path_into_db(root_path="C:/", db=db, reader=reader)

    return fs, db, db.db_path


# =============================================================================
# Test Functions
# =============================================================================

def test_query_respond() -> None:
    """Test query_respond branch - single value queries."""
    print("\n" + "="*70)
    print("TESTING: query_respond (single value queries)")
    print("="*70)

    _, _, db_path = setup_test_filesystem("respond")
    NOW = "2026-02-15 12:00:00"

    # Test 1: Count query
    result = run_test(
        "Count MP3 files",
        "How many MP3 files do I have?",
        db_path, NOW,
        expected_action="query_respond"
    )
    rows = result.get('query_result', [])
    if rows:
        count = list(rows[0].values())[0]
        assert count == 6, f"Expected 6 MP3 files, got {count}"
        print("COUNT CHECK PASSED: 6 MP3 files")

    # Test 2: Sum/aggregate query
    result = run_test(
        "Total music duration",
        "How many minutes of Beatles music do I have?",
        db_path, NOW,
        expected_action="query_respond"
    )

    # Test 3: Yes/No question
    run_test(
        "Yes/No question",
        "Do I have any files older than a month?",
        db_path, NOW,
        expected_action="query_respond"
    )


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
        "Show me all the files in C:/Music/Beatles",
        db_path, NOW,
        expected_action="query_display"
    )

    # Test: List with criteria
    run_test(
        "List files with criteria",
        "List all text files I have",
        db_path, NOW,
        expected_action="query_display"
    )


def test_query_store():
    """Test query_store branch - multi-turn dialog storage."""
    print("\n" + "="*70)
    print("TESTING: query_store (multi-turn storage)")
    print("="*70)

    _, _, db_path = setup_test_filesystem("store")
    NOW = "2026-02-15 12:00:00"

    # Test: Store for later reference
    result = run_test(
        "Store files for later",
        "Remember the MP3 files in my Beatles folder",
        db_path, NOW,
        expected_action="query_store"
    )

    # Check that table was stored
    assert result.get('stored_table') is not None, "Expected stored_table to be set"
    print(f"STORED TABLE CHECK PASSED: {len(result['stored_table'])} rows stored")


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


def test_query_feed_llm():
    """Test query_feed_llm branch - AI processing."""
    print("\n" + "="*70)
    print("TESTING: query_feed_llm (AI processing)")
    print("="*70)

    _, _, db_path = setup_test_filesystem("feed_llm")
    NOW = "2026-02-15 12:00:00"

    run_test(
        "AI rename files",
        "Use AI to suggest better names for my vacation photos based on their metadata",
        db_path, NOW,
        expected_action="query_feed_llm"
    )


def test_query_external():
    """Test query_external branch - external app invocation."""
    print("\n" + "="*70)
    print("TESTING: query_external (external app)")
    print("="*70)

    _, _, db_path = setup_test_filesystem("external")
    NOW = "2026-02-15 12:00:00"

    run_test(
        "Run external app",
        "Run ffmpeg to convert all my MP3 files to WAV format",
        db_path, NOW,
        expected_action="query_external"
    )


def test_web_search():
    """Test web_search branch - web research queries."""
    print("\n" + "="*70)
    print("TESTING: web_search (web research)")
    print("="*70)

    _, _, db_path = setup_test_filesystem("web")
    NOW = "2026-02-15 12:00:00"

    # Use a question that clearly requires current web information
    run_test(
        "Web search - current info needed",
        "What is the current price of the latest Beatles vinyl reissue on Amazon?",
        db_path, NOW,
        expected_action="web_search"
    )


def test_direct_answer():
    """Test direct_answer branch - conversational queries."""
    print("\n" + "="*70)
    print("TESTING: direct_answer (conversational)")
    print("="*70)

    _, _, db_path = setup_test_filesystem("direct")
    NOW = "2026-02-15 12:00:00"

    # Test: Greeting
    run_test(
        "Greeting",
        "Hello, how are you today?",
        db_path, NOW,
        expected_action="direct_answer"
    )

    # Test: General question
    run_test(
        "General question",
        "What can you help me with?",
        db_path, NOW,
        expected_action="direct_answer"
    )


def test_all_branches():
    """Run all branch tests."""
    print("\n" + "#"*70)
    print("# RUNNING ALL BRANCHING AGENT TESTS")
    print("#"*70)

    #test_query_respond()
    test_query_display()
    test_query_store()
    test_query_transform()
    test_query_copy()
    test_query_feed_llm()
    test_query_external()
    test_web_search()
    test_direct_answer()

    print("\n" + "#"*70)
    print("# ALL TESTS COMPLETED")
    print("#"*70)


if __name__ == "__main__":
    # Run individual test or all tests
    # test_query_respond()
    # test_direct_answer()
    test_all_branches()