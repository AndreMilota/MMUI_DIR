# Simple runnable script for tracing the MockFiles interface.
# Run from project root:  python -m file_scan.mock_file_system.test_fs_reader_using_mocks

import os
import sys
from datetime import datetime
from pathlib import Path

# Allow direct execution from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from file_scan.mock_file_system.mock_files import MockFiles


def ns_to_str(ns_value):
    """Convert nanoseconds since epoch to a human-readable string."""
    if ns_value is None:
        return "(none)"
    seconds = ns_value / 1_000_000_000
    return datetime.fromtimestamp(seconds).strftime("%Y-%m-%d %H:%M:%S")


def test_1():
    db_path = "vsf_1.sqlite"

    # clean up any leftover database from a previous run
    if os.path.exists(db_path):
        os.unlink(db_path)

    virtual_fs = MockFiles(db_path)

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
    file_list = virtual_fs.ls()
    print(f"Files in {virtual_fs.getcwd()}:")
    print(f"{'Name':<20} {'Size':>8}  {'Modified':<20} {'Created':<20}")
    print("-" * 72)
    for f in file_list:
        name = f"{f['name']}.{f['extension']}" if f['extension'] else f['name']
        print(f"{name:<20} {f['size_bytes']:>8}  "
              f"{ns_to_str(f['mtime_ns']):<20} {ns_to_str(f['ctime_ns']):<20}")

    print(f"\nClock is now: {ns_to_str(virtual_fs.get_time())}")

    # clean up
    virtual_fs.db.close()
    os.unlink(db_path)


if __name__ == "__main__":
    test_1()
