"""
fs_load.py

High-level loader that ties fs_reader and FSDatabase together.

Default CLI usage (no args):
    - root_path = user's Downloads folder
    - db_path   = "file_database.sqlite" in the same directory as this script

From Python code:
    from fs_load import scan_path_into_db
    db = scan_path_into_db("C:\\Users\\owner\\Downloads", "file_database.sqlite")
"""

import os
from pathlib import Path
from typing import Optional

from fs_reader import (
    get_volume_info,
    iter_dirs,
    iter_files_in_directory,
    collect_full_record,
    directory_fingerprint,
)
from fs_database import FSDatabase


def _normalize_dir_path(path: str) -> str:
    """
    Normalize a directory path to the same style fs_reader uses
    in build_identity: absolute, with forward slashes.
    """
    p = Path(path).resolve()
    return p.as_posix()


def scan_path_into_db(root_path: str, db_path: str) -> FSDatabase:
    """
    Scan all directories and files under root_path and load/update them
    into the SQLite database at db_path.

    - If the database does not exist, it is created.
    - Volume metadata is upserted into 'volumes'.
    - Directories (including empty ones) are upserted into 'directories'.
    - Files are upserted into 'files'.
    - presence_state is maintained using the directory-level scan protocol.
    """
    # Ensure absolute path
    root_path = os.path.abspath(root_path)

    # Create/open the database (this will create tables if needed)
    db = FSDatabase(db_path)

    # ----- Volume -------------------------------------------------------
    vinfo = get_volume_info(root_path)
    volume_id = db.upsert_volume(
        volume_key=vinfo["volume_key"],
        root_path=vinfo.get("root_path"),
        label=vinfo.get("label"),
        filesystem=vinfo.get("filesystem"),
        serial_number=vinfo.get("serial_number"),
    )

    # ----- Directories + files -----------------------------------------
    # We now drive the scan by directories, including empty ones.
    for dir_path_raw in iter_dirs(root_path):
        dir_norm = _normalize_dir_path(dir_path_raw)
        dir_fp = directory_fingerprint(dir_path_raw)

        # Upsert the directory row (one per volume_id + dir_path)
        directory_id = db.upsert_directory(
            volume_id=volume_id,
            dir_path=dir_norm,
            dir_fingerprint=dir_fp,
        )

        # Start a scan for this directory: mark existing files as PENDING_SCAN
        db.begin_directory_scan(directory_id)

        # For each file directly in this directory, upsert the file record.
        for entry, st in iter_files_in_directory(dir_path_raw):
            rec = collect_full_record(dir_path_raw, entry, st)
            db.upsert_file_record(
                directory_id=directory_id,
                record=rec,
            )

        # End the scan for this directory:
        #   - any files still in PENDING_SCAN become MISSING
        db.end_directory_scan(directory_id, completed=True)

    return db


# ---------------------------------------------------------------------- #
# CLI entry point
# ---------------------------------------------------------------------- #

if __name__ == "__main__":
    import sys

    # Root to scan: user's real Downloads folder
    downloads_dir = Path.home() / "Downloads"
    default_root = str(downloads_dir)

    # DB location: project folder (same directory as this script)
    script_dir = Path(__file__).resolve().parent
    default_db = str(script_dir / "file_database.sqlite")

    if len(sys.argv) >= 2:
        root = sys.argv[1]
    else:
        root = default_root

    if len(sys.argv) >= 3:
        db_file = sys.argv[2]
    else:
        db_file = default_db

    print(f"Scanning {root!r} into database {db_file!r} ...")
    db_instance = scan_path_into_db(root, db_file)
    print("Scan completed.")
