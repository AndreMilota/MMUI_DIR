"""
fs_debug.py

Debug helper for the Agentic File Manager.

- Uses pure Python (os.walk) to recursively list all files under a root path.
- Reconstructs all file paths from the SQLite database.
- Compares the two sets and reports discrepancies.

Default usage (no args):
    - root_path = user's Downloads folder
    - db_path   = file_database.sqlite in the project folder

You can also override:
    python fs_debug.py <root_path> [db_path]
"""

import os
import sqlite3
import sys
from pathlib import Path
from typing import List, Set


# ---------------------------------------------------------------------------
# Path normalization
# ---------------------------------------------------------------------------

def normalize_path_for_compare(p: str) -> str:
    """
    Normalize a path so we can compare DB vs filesystem safely:

        - resolve to an absolute path
        - use forward slashes
        - lower-case (good enough for Windows)
    """
    return Path(p).resolve().as_posix().lower()


# ---------------------------------------------------------------------------
# Python-based file listing (ground truth for disk)
# ---------------------------------------------------------------------------

def list_files_via_python(root_path: str) -> List[str]:
    """
    Pure Python recursive file listing using os.walk.
    """
    root_path = os.path.abspath(root_path)
    out: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        for name in filenames:
            full = os.path.join(dirpath, name)
            out.append(full)
    return out


# ---------------------------------------------------------------------------
# DB-based file listing
# ---------------------------------------------------------------------------

def get_db_file_paths_for_root(db_path: Path, root_path: str) -> List[str]:
    """
    Reconstruct full paths for all files in the DB that live under the
    given root_path.

    We join directories.dir_path with files.name + extension, then keep
    only those whose full path starts with root_path (after normalization).
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT d.dir_path, f.name, f.extension
            FROM files f
            JOIN directories d ON f.directory_id = d.id;
            """
        )

        root_norm = normalize_path_for_compare(root_path)
        paths: List[str] = []

        for row in cur:
            dir_path_norm = row["dir_path"]  # already POSIX-style from fs_reader
            name = row["name"]
            ext = row["extension"]

            if ext:
                filename = f"{name}.{ext}"
            else:
                filename = name

            full = Path(dir_path_norm) / filename
            full_norm = normalize_path_for_compare(str(full))

            if full_norm.startswith(root_norm):
                paths.append(full_norm)

        return paths

    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Comparison logic
# ---------------------------------------------------------------------------

def compare_python_vs_db(root_path: str, db_path: str) -> None:
    """
    Compare Python-recursed file list vs DB file list for a given root.
    """
    print(f"Root path: {root_path}")
    print(f"Database: {db_path}")
    print()

    # Python listing (ground truth for disk)
    print("Listing files via Python (os.walk)...")
    py_raw = list_files_via_python(root_path)
    py_norm_set: Set[str] = {normalize_path_for_compare(p) for p in py_raw}
    print(f"  Python-reported files: {len(py_norm_set)}")
    print()

    # DB listing
    print("Listing files via DB...")
    db_file_paths = get_db_file_paths_for_root(Path(db_path), root_path)
    db_norm_set: Set[str] = set(db_file_paths)
    print(f"  DB-reconstructed files: {len(db_norm_set)}")
    print()

    # Differences
    only_on_disk = sorted(py_norm_set - db_norm_set)
    only_in_db = sorted(db_norm_set - py_norm_set)

    print(f"Files only on disk (Python, not in DB): {len(only_on_disk)}")
    print(f"Files only in DB (not seen by Python): {len(only_in_db)}")
    print()

    max_show = 50

    if only_on_disk:
        print(f"Sample of files only on disk (up to {max_show}):")
        for p in only_on_disk[:max_show]:
            print(f"  [disk-only] {p}")
        print()

    if only_in_db:
        print(f"Sample of files only in DB (up to {max_show}):")
        for p in only_in_db[:max_show]:
            print(f"  [db-only] {p}")
        print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Defaults: Downloads as root, project dir DB.
    script_dir = Path(__file__).resolve().parent
    default_root = str(Path.home() / "Downloads")
    default_db = str(script_dir / "file_database.sqlite")

    if len(sys.argv) >= 2:
        root = sys.argv[1]
    else:
        root = default_root

    if len(sys.argv) >= 3:
        db_file = sys.argv[2]
    else:
        db_file = default_db

    compare_python_vs_db(root, db_file)
