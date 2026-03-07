# scripts/app_2/test_web_search.py
"""
Tests for the web_search branch of the app_2 LangGraph workflow.

web_search handles queries that require current information from the
internet - things the agent cannot answer from the local file database
alone (e.g., current prices, recent events, live data).
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
# TEST FILESYSTEM SETUP
# Source: branching_agent_tests.py
# Rich mock filesystem with music, documents, and pictures.
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
# FROM: branching_agent_tests.py
# ===========================================================================

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


# ===========================================================================
# TEST RUNNER
# ===========================================================================

def test_all_web_search():
    """Run all web_search tests."""
    print("\n" + "#"*70)
    print("# RUNNING ALL web_search TESTS")
    print("#"*70)

    test_web_search()

    print("\n" + "#"*70)
    print("# web_search TESTS COMPLETED")
    print("#"*70)


if __name__ == "__main__":
    test_all_web_search()
