# This file the agent can only return answers about the number or presence of particular The states of the file syste
# import the database
import os
from datetime import datetime

from file_scan.fs_database import FSDatabase
from file_scan.fs_load import scan_path_into_db
from file_scan.mock_file_system.mock_files import MockFiles
from file_scan.mock_file_system.mock_fs_reader import MockFSReader
from app.runner import run_query
from pathlib import Path
from file_scan.tests.export_db import export_all_tables

def ns_to_str(ns_value):
    """Convert nanoseconds since epoch to a human-readable string."""
    if ns_value is None:
        return "(none)"
    seconds = ns_value / 1_000_000_000
    return datetime.fromtimestamp(seconds).strftime("%Y-%m-%d %H:%M:%S")

def make_new_file_system(name: str = "test_fs") -> MockFiles:
    #clear the database file if it exists
    db_filename = f"{name}.sqlite"
    if os.path.exists(db_filename):
        os.unlink(db_filename)
    vfs = MockFiles(db_path=db_filename)
    vfs.set_time("2026-01-01 12:00:00")
    vfs.mount_volume(drive_letter='C')
    return vfs

def get_fresh_database(name: str = "test_db") -> FSDatabase:
    # clear the database file if it exists
    db_path = f"{name}.sqlite"
    if os.path.exists(db_path):
        os.unlink(db_path)
    db = FSDatabase(db_path)
    return db

def ls(virtual_fs: MockFiles):
    """List all files in the database for debugging.
    displays the file path with extension and size in bytes and time created and Modified.
    writes Headings at the top. and puts tabs between columns.
    """
    # print headings
    print(f"{'File Path':<40}\t{'Size (bytes)':<15}\t{'Created':<20}\t{'Modified':<20}")

    files = virtual_fs.ls()
    for f in files:
        name = f"{f['name']}.{f['extension']}" if f['extension'] else f['name']
        print(f"{name:<40}\t{f['size_bytes']:<15}\t{ns_to_str(f['ctime_ns']):<20}\t{ns_to_str(f['mtime_ns']):<20}")

def run_test_query(label, query, db_path, now, expected=None):
    """Run a query, print results, optionally assert on count."""
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"QUERY: {query}")
    result = run_query(query, now=now, db_path=db_path)
    print(f"SQL:\n{result['sql']}")
    if result.get('error'):
        print(f"ERROR: {result['error']}")
    else:
        rows = result.get('results', [])
        print(f"ROWS: {rows}")
        print(f"RESPONSE: {result.get('response')}")
    print(f"{'='*60}")
    return result


def test_1():
    # Set up the virtual file system
    fs = make_new_file_system("simple_agent_fs")

    # add a file
    fs.save("beatles_best_of.mp3", size_bytes=5000)

     # Verify the file is in the database
    files = fs.ls()
    assert len(files) == 1, f"Expected 1 file, got {len(files)}"
    assert files[0]['name'] == 'beatles_best_of', f"Unexpected name: {files[0]['name']}"
    print(f"OK: found {files[0]['name']}.{files[0]['extension']} ({files[0]['size_bytes']} bytes)")

    # print the directory listing from the database
    ls(fs)

    # get a fresh database
    db = get_fresh_database()

    # scan the virtual file system into the database
    reader = MockFSReader(fs)
    scan_path_into_db(root_path="C:/", db=db, reader=reader)

    # export_all_tables(
    #     db_path=Path(db.db_path),
    #     out_dir=Path(os.path.dirname(db.db_path) or "."),
    #     tables=["volumes", "directories", "files"],
    # )

    # ------------------------------------------------------------------
    # Run the LangGraph query pipeline against the scan database
    # ------------------------------------------------------------------

    # The mock file was created at 2026-01-01 12:00:00.
    # Set "now" two weeks later so the file counts as "more than a week old".
    query = "How many mp3 files do I have that are more than a week old?"
    print(f"\n{'='*60}")
    print(f"USER QUERY: {query}")
    print(f"{'='*60}\n")

    result = run_query(query, now="2026-01-15 12:00:00", db_path=db.db_path)

    print(f"GENERATED SQL:\n{result['sql']}\n")
    print(f"{'='*60}")

    if result.get('error'):
        print(f"ERROR: {result['error']}\n")
    else:
        print(f"FOUND {len(result.get('results', []))} ROWS\n")
        print(f"RESPONSE:\n{result.get('response')}\n")

    print(f"{'='*60}\n")

    rows = result.get('results', [])
    count = list(rows[0].values())[0]
    assert count == 1, f"Expected 1 mp3 file, got {count}"
    print(f"ASSERTION PASSED: count = {count}")


def test_q1_three_weeks_old():
    """Focused test for: 'How many text files are there which are three weeks old?'
    NOW = Feb 15 12:00.  Three weeks ago = Jan 25 12:00.
    Files with ctime <= Jan 25: old_notes (Jan 8), quarterly_report (Jan 10),
    annual_summary (Jan 15), budget_draft (Jan 20) → 4.
    Files with ctime > Jan 25: meeting_notes (Feb 10), empty_template (Feb 12),
    cover_letter (Feb 10), blank (Feb 11) → not three weeks old.
    """
    NOW = "2026-02-15 12:00:00"

    fs = make_new_file_system("test_q1_fs")
    fs.mkdir("C:/Documents/Reports")
    fs.mkdir("C:/Documents/Letters")

    # --- 4 files that ARE three weeks old (ctime <= Jan 25) ---
    fs.cd("C:/Documents/Reports")
    fs.set_time("2026-01-08 00:00:00")
    fs.save("old_notes.txt", size_bytes=600)
    fs.set_time("2026-01-10 00:00:00")
    fs.save("quarterly_report.txt", size_bytes=2048)
    fs.set_time("2026-01-15 00:00:00")
    fs.save("annual_summary.txt", size_bytes=4096)
    fs.set_time("2026-01-20 00:00:00")
    fs.save("budget_draft.txt", size_bytes=1024)

    # --- 4 files that are NOT three weeks old ---
    fs.set_time("2026-02-10 09:00:00")
    fs.save("meeting_notes.txt", size_bytes=512)
    fs.set_time("2026-02-12 00:00:00")
    fs.save("empty_template.txt", size_bytes=0)

    fs.cd("C:/Documents/Letters")
    fs.set_time("2026-02-10 09:00:00")
    fs.save("cover_letter.txt", size_bytes=300)
    fs.set_time("2026-02-11 00:00:00")
    fs.save("blank.txt", size_bytes=0)

    # Scan
    db = get_fresh_database("test_q1_db")
    reader = MockFSReader(fs)
    scan_path_into_db(root_path="C:/", db=db, reader=reader)

    # Query
    result = run_test_query(
        "Q1: Text files three weeks old",
        "How many text files are there which are three weeks old?",
        db.db_path, NOW)

    rows = result.get('results', [])
    count = list(rows[0].values())[0] if rows else None
    assert count == 4, f"Q1: expected 4, got {count}"
    print("Q1 PASSED")


def test_2():
    NOW = "2026-02-15 12:00:00"

    # ── Build virtual filesystem ──────────────────────────────────
    fs = make_new_file_system("test2_fs")

    # Directory tree
    fs.mkdir("C:/Documents/Reports")
    fs.mkdir("C:/Documents/Letters")
    fs.mkdir("C:/Documents/Drafts")
    fs.mkdir("C:/Music/Beatles")
    fs.mkdir("C:/Music/Rock")
    fs.mkdir("C:/Music/Jazz")
    fs.mkdir("C:/Music/Recordings")
    fs.mkdir("C:/Shared/ProjectA")
    fs.mkdir("C:/Shared/ProjectB")
    fs.mkdir("C:/Shared/ProjectC")

    # ── Documents/Reports ─────────────────────────────────────────
    fs.cd("C:/Documents/Reports")
    fs.set_time("2026-01-08 00:00:00")
    fs.save("old_notes.txt", size_bytes=600)
    fs.set_time("2026-01-10 00:00:00")
    fs.save("quarterly_report.txt", size_bytes=2048)
    fs.set_time("2026-01-15 00:00:00")
    fs.save("annual_summary.txt", size_bytes=4096)
    fs.set_time("2026-01-20 00:00:00")
    fs.save("budget_draft.txt", size_bytes=1024)
    fs.set_time("2026-02-10 09:00:00")
    fs.save("meeting_notes.txt", size_bytes=512)
    fs.set_time("2026-02-12 00:00:00")
    fs.save("empty_template.txt", size_bytes=0)

    # ── Documents/Letters ─────────────────────────────────────────
    fs.cd("C:/Documents/Letters")
    fs.set_time("2026-02-10 09:00:00")
    fs.save("cover_letter.txt", size_bytes=300)
    fs.set_time("2026-02-08 00:00:00")
    fs.save("thank_you.txt", size_bytes=400)          # will be deleted
    fs.set_time("2026-02-11 00:00:00")
    fs.save("blank.txt", size_bytes=0)

    # ── Documents/Drafts ──────────────────────────────────────────
    fs.cd("C:/Documents/Drafts")
    fs.set_time("2026-02-12 14:00:00")
    fs.save("proposal.txt", size_bytes=1500)
    fs.save("outline.doc", size_bytes=800)             # same ctime as proposal

    # ── Music/Beatles (artist="The Beatles", channels=2) ─────────
    fs.cd("C:/Music/Beatles")
    fs.set_file_defaults(tag_artist="The Beatles", channels=2)

    fs.set_time("2026-01-05 00:00:00")
    fs.save_m("yesterday.mp3", duration=180, bitrate=320000)
    fs.set_time("2026-01-18 00:00:00")
    fs.save_m("let_it_be.mp3", duration=240, bitrate=320000)
    fs.set_time("2026-01-20 00:00:00")
    fs.save_m("penny_lane.mp3", duration=180, bitrate=320000)
    fs.set_time("2026-01-22 00:00:00")
    fs.save_m("blackbird.mp3", duration=240, bitrate=128000)
    fs.set_time("2026-02-14 00:00:00")
    fs.save_m("hey_jude.mp3", duration=55, bitrate=320000)
    fs.save_m("come_together.wav", duration=250, bitrate=320000)
    fs.set_time("2026-02-13 00:00:00")
    fs.save_m("help.mp3", duration=55, bitrate=320000)

    # ── Music/Rock (channels=2, artist per-file) ─────────────────
    fs.cd("C:/Music/Rock")
    fs.set_file_defaults(tag_artist=None, channels=2)

    fs.set_time("2026-02-03 00:00:00")
    fs.save_m("bohemian_rhapsody.mp3", duration=354, bitrate=320000,
              tag_artist="Queen")
    fs.set_time("2026-02-05 00:00:00")
    fs.save_m("stairway_to_heaven.mp3", duration=482, bitrate=320000,
              tag_artist="Led Zeppelin")
    fs.set_time("2026-01-25 00:00:00")
    fs.save_m("smoke_on_water.mp3", duration=180, bitrate=320000,
              tag_artist="Deep Purple")

    # ── Music/Jazz (artist + channels per-file) ──────────────────
    fs.cd("C:/Music/Jazz")
    fs.set_file_defaults(tag_artist=None, channels=None)

    fs.set_time("2026-02-01 00:00:00")
    fs.save_m("take_five.mp3", duration=324, bitrate=128000,
              tag_artist="Dave Brubeck", channels=1)
    fs.set_time("2026-02-02 00:00:00")
    fs.save_m("so_what.mp3", duration=561, bitrate=128000,
              tag_artist="Miles Davis", channels=1)
    fs.set_time("2026-01-28 00:00:00")
    fs.save_m("autumn_leaves.mp3", duration=300, bitrate=128000,
              tag_artist="Bill Evans", channels=2)     # will be deleted

    # ── Music/Recordings (no artist) ─────────────────────────────
    fs.cd("C:/Music/Recordings")
    fs.set_file_defaults(tag_artist=None)

    fs.set_time("2026-02-14 00:00:00")
    fs.save_m("voice_memo_1.mp3", duration=15, bitrate=128000, channels=1)
    fs.save_m("voice_memo_2.mp3", duration=25, bitrate=128000, channels=2)
    fs.save_m("meeting_recording.mp3", duration=3600, bitrate=128000, channels=2)
    fs.save_m("quick_note.wav", duration=10, bitrate=128000, channels=2)

    # ── Shared projects ──────────────────────────────────────────
    fs.set_file_defaults(tag_artist=None, channels=None)

    fs.cd("C:/Shared/ProjectA")
    fs.save("data.csv", size_bytes=1024)
    fs.save("readme.txt", size_bytes=512)

    fs.cd("C:/Shared/ProjectB")
    fs.save("data.csv", size_bytes=1024)
    fs.save("notes.txt", size_bytes=768)

    fs.cd("C:/Shared/ProjectC")
    fs.save("data.csv", size_bytes=1024)
    fs.save("report.txt", size_bytes=512)

    # ── Initial scan ──────────────────────────────────────────────
    db = get_fresh_database("test2_db")
    reader = MockFSReader(fs)
    scan_path_into_db(root_path="C:/", db=db, reader=reader)

    # ── Delete 2 files, then rescan ──────────────────────────────
    fs.delete("C:/Documents/Letters/thank_you.txt")
    fs.delete("C:/Music/Jazz/autumn_leaves.mp3")

    reader = MockFSReader(fs)
    scan_path_into_db(root_path="C:/", db=db, reader=reader)

    db_path = db.db_path

    # ==============================================================
    # Q1: "How many text files are there which are three weeks old?"
    # Expected: 4 (old_notes Jan 8, quarterly_report Jan 10,
    #              annual_summary Jan 15, budget_draft Jan 20)
    # ==============================================================
    result = run_test_query(
        "Q1: Text files three weeks old",
        "How many text files are there which are three weeks old?",
        db_path, NOW)
    rows = result.get('results', [])
    count = list(rows[0].values())[0] if rows else None
    assert count == 4, f"Q1: expected 4, got {count}"
    print("Q1 PASSED")

    # ==============================================================
    # Q2: "How many text files are there in C:/Documents/Reports?"
    # Expected: 6
    # ==============================================================
    result = run_test_query(
        "Q2: Text files in Reports",
        "How many text files are there in C:/Documents/Reports?",
        db_path, NOW)
    rows = result.get('results', [])
    count = list(rows[0].values())[0] if rows else None
    assert count == 6, f"Q2: expected 6, got {count}"
    print("Q2 PASSED")

    # ==============================================================
    # Q3: "Are there any zero length text files in C:/Documents/Reports?"
    # Expected: Yes (empty_template.txt)
    # ==============================================================
    result = run_test_query(
        "Q3: Zero-length text files in Reports",
        "Are there any zero length text files in C:/Documents/Reports?",
        db_path, NOW)
    response = (result.get('response') or '').lower()
    assert 'yes' in response or len(result.get('results', [])) > 0, \
        f"Q3: expected 'yes' in response"
    print("Q3 PASSED (soft)")

    # ==============================================================
    # Q4: "Are there any files with the exact same creation timestamp
    #      in the children of C:/Documents?"
    # Expected: Yes (meeting_notes + cover_letter at Feb 10 09:00,
    #                proposal + outline at Feb 12 14:00)
    # ==============================================================
    result = run_test_query(
        "Q4: Duplicate creation timestamps in Documents children",
        "Are there any files with the exact same creation timestamp "
        "in the children of C:/Documents?",
        db_path, NOW)
    response = (result.get('response') or '').lower()
    assert 'yes' in response or len(result.get('results', [])) > 0, \
        f"Q4: expected 'yes' in response"
    print("Q4 PASSED (soft)")

    # ==============================================================
    # Q5: "Are there any MP3 files that are shorter than a minute
    #      in C:/Music recursively?"
    # Expected: 4 (hey_jude 55s, help 55s, voice_memo_1 15s,
    #              voice_memo_2 25s)
    # ==============================================================
    result = run_test_query(
        "Q5: MP3s shorter than a minute in Music",
        "Are there any MP3 files that are shorter than a minute "
        "in C:/Music recursively?",
        db_path, NOW)
    rows = result.get('results', [])
    # The LLM may return a count or a list of rows
    if rows and len(rows) == 1 and len(rows[0]) == 1:
        count = list(rows[0].values())[0]
    else:
        count = len(rows)
    assert count == 4, f"Q5: expected 4, got {count}"
    print("Q5 PASSED")

    # ==============================================================
    # Q6: "Are there any duplicate files in C:/Shared/ProjectA,
    #      C:/Shared/ProjectB, and C:/Shared/ProjectC?"
    # Expected: Yes (data.csv × 3) — ambiguous definition
    # ==============================================================
    result = run_test_query(
        "Q6: Duplicate files across Shared projects",
        "Are there any duplicate files in C:/Shared/ProjectA, "
        "C:/Shared/ProjectB, and C:/Shared/ProjectC?",
        db_path, NOW)
    print("Q6 ANALYSIS (ambiguous — 'duplicate' could mean same name, "
          "same name+size, or same content):")
    print(f"  SQL returned {len(result.get('results', []))} rows")
    print(f"  data.csv appears 3× with identical size (1024 bytes)")

    # ==============================================================
    # Q7: "How many MP3 files are there that were created last week?"
    # Expected: 2–5 depending on "last week" interpretation
    # ==============================================================
    result = run_test_query(
        "Q7: MP3s created last week",
        "How many MP3 files are there that were created last week?",
        db_path, NOW)
    rows = result.get('results', [])
    count = list(rows[0].values())[0] if rows else None
    # ── "Last week" is ambiguous with now = Sunday Feb 15 ──
    # Mon–Sun calendar week (Feb 2–8):
    #   so_what (Feb 2), bohemian_rhapsody (Feb 3),
    #   stairway_to_heaven (Feb 5) → 3
    # Sun–Sat calendar week (Feb 8–14):
    #   help (Feb 13), hey_jude (Feb 14), voice_memo_1 (Feb 14),
    #   voice_memo_2 (Feb 14), meeting_recording (Feb 14) → 5
    # 7–14 days ago (Feb 1–8):
    #   take_five (Feb 1), so_what (Feb 2), bohemian_rhapsody (Feb 3),
    #   stairway_to_heaven (Feb 5) → 4
    print(f"Q7 ANALYSIS: LLM returned {count}")
    print("  Mon-Sun calendar week (Feb 2-8):  3  (so_what, bohemian, stairway)")
    print("  Sun-Sat calendar week (Feb 8-14): 5  (help, hey_jude, vm1, vm2, meeting)")
    print("  7-14 days ago (Feb 1-8):          4  (take_five, so_what, bohemian, stairway)")

    # ==============================================================
    # Q8: "How many MP3 files were created last month that are exactly
    #      the same length as one another?"
    # Expected: 5 (yesterday 180s + penny_lane 180s + smoke_on_water 180s
    #              + let_it_be 240s + blackbird 240s)
    # ==============================================================
    result = run_test_query(
        "Q8: Last-month MP3s with matching durations",
        "How many MP3 files were created last month that are exactly "
        "the same length as one another?",
        db_path, NOW)
    rows = result.get('results', [])
    if rows and len(rows) == 1 and len(rows[0]) == 1:
        count = list(rows[0].values())[0]
    else:
        count = len(rows)
    assert count == 5, f"Q8: expected 5, got {count}"
    print("Q8 PASSED")

    # ==============================================================
    # Q9: "Did I add MP3s or WAVs of songs by the Beatles yesterday
    #      or the day before?"
    # Expected: Yes (hey_jude, come_together, help)
    # ==============================================================
    result = run_test_query(
        "Q9: Beatles MP3/WAV yesterday or day before",
        "Did I add MP3s or WAVs of songs by the Beatles yesterday "
        "or the day before?",
        db_path, NOW)
    response = (result.get('response') or '').lower()
    assert 'yes' in response or len(result.get('results', [])) > 0, \
        f"Q9: expected 'yes' in response"
    print("Q9 PASSED (soft)")

    # ==============================================================
    # Q10: "Did I add any media files by the Beatles last month?"
    # Expected: Yes (yesterday, let_it_be, penny_lane, blackbird)
    # ==============================================================
    result = run_test_query(
        "Q10: Beatles media files last month",
        "Did I add any media files by the Beatles last month?",
        db_path, NOW)
    response = (result.get('response') or '').lower()
    assert 'yes' in response or len(result.get('results', [])) > 0, \
        f"Q10: expected 'yes' in response"
    print("Q10 PASSED (soft)")

    # ==============================================================
    # Q11: "How many minutes of audio are in audio files in
    #       C:/Music/Beatles?"
    # Expected: 20.0 minutes (1200 seconds total)
    # (180+240+180+240+55+250+55 = 1200s = 20 min)
    # ==============================================================
    result = run_test_query(
        "Q11: Total minutes of audio in Beatles folder",
        "How many minutes of audio are in audio files in "
        "C:/Music/Beatles?",
        db_path, NOW)
    rows = result.get('results', [])
    value = list(rows[0].values())[0] if rows else None
    assert value == 20.0, f"Q11: expected 20.0, got {value}"
    print("Q11 PASSED")

    # ==============================================================
    # Q12: "How many mono files do I have?"
    # Expected: 3 (take_five, so_what, voice_memo_1)
    # (autumn_leaves was deleted, so it's MISSING)
    # ==============================================================
    result = run_test_query(
        "Q12: Mono files",
        "How many mono files do I have?",
        db_path, NOW)
    rows = result.get('results', [])
    count = list(rows[0].values())[0] if rows else None
    assert count == 3, f"Q12: expected 3, got {count}"
    print("Q12 PASSED")

    # ==============================================================
    # Q13: "How many files did I record yesterday that are under
    #       30 seconds and are in stereo?"
    # Expected: 2 (voice_memo_2 25s ch=2, quick_note 10s ch=2)
    # ==============================================================
    result = run_test_query(
        "Q13: Stereo files under 30s recorded yesterday",
        "How many files did I record yesterday that are under "
        "30 seconds and are in stereo?",
        db_path, NOW)
    rows = result.get('results', [])
    count = list(rows[0].values())[0] if rows else None
    assert count == 2, f"Q13: expected 2, got {count}"
    print("Q13 PASSED")

    print("\n" + "="*60)
    print("test_2: ALL QUERIES COMPLETE")
    print("="*60)


if __name__ == "__main__":
    test_q1_three_weeks_old()
    # test_1()
    # test_2()

# TODO: Add test for speech-recognition errors and disfluencies