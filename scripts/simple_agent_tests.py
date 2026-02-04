# This file the agent can only return answers about the number or presence of particular The states of the file syste
# import the database
from file_scan.fs_database import FSDatabase
from file_scan.fs_load import scan_path_into_db
import os

def make_new_file_system(name: str = "test_fs") -> "MockFiles":
    from file_scan.mock_file_system.mock_files import MockFiles

    #clear the database file if it exists
    import os
    db_filename = f"{name}.sqlite"
    if os.path.exists(db_filename):
        os.unlink(db_filename)
    vfs = MockFiles(db_path=db_filename)
    vfs.set_time("2026-01-01 12:00:00")
    vfs.mount_volume(drive_letter='C')
    return vfs

def get_fresh_database(name: str = "test_db") -> "FSDatabase":
    # clear the database file if it exists
    db_path = f"{name}.sqlite"
    if os.path.exists(db_path):
        os.unlink(db_path)
    db = FSDatabase(db_path)
    return db

def test_1():
    # Set up the virtual file system
    fs = make_new_file_system("simple_agent_fs")

    # add a file
    fs.save("beatles_best_of.mp3", size_bytes=5000)

    # MockFiles writes directly into its own FSDatabase (fs.db),
    # so no separate scan step is needed.
    db = fs.db

    # Verify the file is in the database
    files = fs.ls()
    assert len(files) == 1, f"Expected 1 file, got {len(files)}"
    assert files[0]['name'] == 'beatles_best_of', f"Unexpected name: {files[0]['name']}"
    print(f"OK: found {files[0]['name']}.{files[0]['extension']} ({files[0]['size_bytes']} bytes)")

if __name__ == "__main__":
    test_1()