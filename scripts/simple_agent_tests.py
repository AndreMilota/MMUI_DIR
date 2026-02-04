# This file the agent can only return answers about the number or presence of particular The states of the file syste
# import the database
import os
from datetime import datetime

from file_scan.fs_database import FSDatabase
from file_scan.fs_load import scan_path_into_db
from file_scan.mock_file_system.mock_files import MockFiles


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


if __name__ == "__main__":
    test_1()