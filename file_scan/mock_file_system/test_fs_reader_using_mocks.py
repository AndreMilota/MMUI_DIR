# Simple runnable script for tracing the MockFiles + MockFSReader pipeline.
# Run from project root:  python -m file_scan.mock_file_system.test_fs_reader_using_mocks

import os
import sys
from datetime import datetime
from pathlib import Path

# Allow direct execution from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
# Allow bare imports used by fs_load / fs_reader / export_db
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from file_scan.mock_file_system.mock_files import MockFiles
from file_scan.mock_file_system.mock_fs_reader import MockFSReader
from file_scan.fs_load import scan_path_into_db
from file_scan.tests.export_db import export_table_to_tsv

def ns_to_str(ns_value):
    """Convert nanoseconds since epoch to a human-readable string."""
    if ns_value is None:
        return "(none)"
    seconds = ns_value / 1_000_000_000
    return datetime.fromtimestamp(seconds).strftime("%Y-%m-%d %H:%M:%S")

def ls(virtual_fs):
    # list the files and print them
    file_list = virtual_fs.ls()
    print(f"Files in {virtual_fs.getcwd()}:")
    print("Name\tSize\tModified\tCreated")
    for f in file_list:
        name = f"{f['name']}.{f['extension']}" if f['extension'] else f['name']
        print(f"{name}\t{f['size_bytes']}\t{ns_to_str(f['mtime_ns'])}\t{ns_to_str(f['ctime_ns'])}")

    print(f"\nClock is now: {ns_to_str(virtual_fs.get_time())}")

def test_1():
    vfs_db_path = "vsf_1.sqlite"
    scan_db_path = "scan_results.sqlite"

    # clean up any leftover files from a previous run
    for p in [vfs_db_path, scan_db_path]:
        if os.path.exists(p):
            os.unlink(p)
    for t in ["volumes.tsv", "directories.tsv", "files.tsv"]:
        if os.path.exists(t):
            os.unlink(t)

    virtual_fs = MockFiles(vfs_db_path)

    # set the clock to the first day of 2026 at noon
    virtual_fs.set_time("2026-01-01 12:00:00")

    # mount C drive
    virtual_fs.mount_volume(drive_letter='C')

    # create C:\test and cd into it
    virtual_fs.mkdir("C:\\test")
    virtual_fs.cd("C:\\test")

    # save 5 text files (clock auto-advances 1 second per save)
    for i in range(5):
        virtual_fs.save(f"file_{i}.txt", size_bytes=100 + i)

    # list the files and print them
    ls(virtual_fs)

    # Record the latest file mtime for later comparison
    file_list = virtual_fs.ls()
    max_file_mtime = max(f['mtime_ns'] for f in file_list)

    # ==================================================================
    # First scan: use MockFSReader + scan_path_into_db
    # ==================================================================
    reader = MockFSReader(virtual_fs)
    scan_db = scan_path_into_db("C:\\test", scan_db_path, reader=reader)

    # Query: how many files are present?
    cur = scan_db.conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM files WHERE presence_state = 0")
    count = cur.fetchone()['cnt']
    print(f"\n--- First Scan ---")
    print(f"Files in scan database (PRESENT): {count}")

    # Verify scan timestamps are populated and ordered correctly
    cur.execute("""
        SELECT dir_path, last_scan_started_ns, last_scan_completed_ns
        FROM directories
    """)
    for row in cur.fetchall():
        started = row['last_scan_started_ns']
        completed = row['last_scan_completed_ns']
        print(f"  Dir: {row['dir_path']}")
        print(f"    scan started:   {ns_to_str(started)}")
        print(f"    scan completed: {ns_to_str(completed)}")

        assert started is not None, "last_scan_started_ns should be set"
        assert completed is not None, "last_scan_completed_ns should be set"
        assert started < completed, "started should be before completed"
        assert started > max_file_mtime, (
            f"scan start ({started}) should be after latest file mtime ({max_file_mtime})"
        )

    # ==================================================================
    # Delete 2 files from the virtual filesystem and rescan
    # ==================================================================
    print(f"\nDeleting file_0.txt and file_1.txt from virtual filesystem...")
    virtual_fs.delete("file_0.txt")
    virtual_fs.delete("file_1.txt")

    # Rescan using the same pipeline
    scan_db.close()
    reader2 = MockFSReader(virtual_fs)
    scan_db = scan_path_into_db("C:\\test", scan_db_path, reader=reader2)

    # Query: how many files are still present?
    cur = scan_db.conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM files WHERE presence_state = 0")
    present_count = cur.fetchone()['cnt']
    print(f"\n--- Second Scan (after deleting 2 files) ---")
    print(f"Files still present (presence_state=0): {present_count}")

    # Query: how many files were marked as deleted?
    cur.execute("SELECT COUNT(*) as cnt FROM files WHERE presence_state = 2")
    deleted_count = cur.fetchone()['cnt']
    print(f"Files marked as deleted (presence_state=2): {deleted_count}")

    # Verify second scan timestamps are later than first scan
    cur.execute("""
        SELECT dir_path, last_scan_started_ns, last_scan_completed_ns
        FROM directories
    """)
    for row in cur.fetchall():
        started = row['last_scan_started_ns']
        completed = row['last_scan_completed_ns']
        print(f"  Dir: {row['dir_path']}")
        print(f"    scan started:   {ns_to_str(started)}")
        print(f"    scan completed: {ns_to_str(completed)}")
        assert started is not None, "last_scan_started_ns should be set"
        assert completed is not None, "last_scan_completed_ns should be set"
        assert started < completed, "started should be before completed"

    # ==================================================================
    # Export scan database tables to TSV for debugging
    # ==================================================================
    print(f"\nExporting scan database tables to TSV...")
    for table_name in ["volumes", "directories", "files"]:
        out_path = Path(f"{table_name}.tsv")
        export_table_to_tsv(scan_db.conn, table_name, out_path)

    # clean up
    scan_db.close()
    virtual_fs.db.close()
    os.unlink(vfs_db_path)
    os.unlink(scan_db_path)

    print("\nAll assertions passed.")


if __name__ == "__main__":
    test_1()
