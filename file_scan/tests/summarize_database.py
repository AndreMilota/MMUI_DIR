"""
summarize_database.py

Summarize a SQLite database file for the Agentic File Manager.

- File size and 16-bit short hash of the DB file.
- Per-table row/column counts, column names, and 16-bit hashes.
- High-level summary:
    - volumes count
    - directories count
    - files count
    - present files (presence_state = 0)
    - system files (system=1, if column exists)
    - symlink files (is_symlink=1, if column exists)

Default DB path: "file_database.sqlite" in the same directory as this script,
or pass a custom path:

    python summarize_database.py
    python summarize_database.py path/to/other_database.sqlite
"""

import hashlib
import sqlite3
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Optional


def short_hash_from_hasher(hasher: "hashlib._hashlib.HASH", hex_digits: int = 4) -> str:
    full_hex = hasher.hexdigest()
    return full_hex[:hex_digits]


def get_db_path_from_args(argv: List[str]) -> Path:
    script_dir = Path(__file__).resolve().parent
    default_db = script_dir / "../file_database.sqlite"
    if len(argv) >= 2:
        return Path(argv[1])
    return default_db


def get_file_size(path: Path) -> int:
    return path.stat().st_size


def short_hash_file(path: Path, chunk_size: int = 1 << 20) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return short_hash_from_hasher(hasher, hex_digits=4)


def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def get_table_names(conn: sqlite3.Connection) -> List[str]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name;
        """
    )
    return [row["name"] for row in cur.fetchall()]


def get_table_dimensions_and_columns(
    conn: sqlite3.Connection,
    table_name: str,
) -> Tuple[int, int, List[str]]:
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table_name} LIMIT 1;")
    col_names = [desc[0] for desc in cur.description] if cur.description else []
    cur.execute(f"SELECT COUNT(*) AS cnt FROM {table_name};")
    n_rows = int(cur.fetchone()["cnt"])
    n_cols = len(col_names)
    return n_rows, n_cols, col_names


def row_to_bytes(row: sqlite3.Row, col_names: List[str]) -> bytes:
    parts = []
    for name in col_names:
        value = row[name]
        if value is None:
            parts.append("<NULL>")
        else:
            parts.append(str(value))
    line = "\t".join(parts)
    return line.encode("utf-8")


def hash_table_and_columns(
    conn: sqlite3.Connection,
    table_name: str,
) -> Tuple[str, Dict[str, str]]:
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table_name};")
    col_names = [desc[0] for desc in cur.description] if cur.description else []

    table_hasher = hashlib.sha256()
    col_hashers: Dict[str, "hashlib._hashlib.HASH"] = {
        name: hashlib.sha256() for name in col_names
    }

    for row in cur:
        row_bytes = row_to_bytes(row, col_names)
        table_hasher.update(row_bytes + b"\n")
        for name in col_names:
            value = row[name]
            token = "<NULL>" if value is None else str(value)
            col_hashers[name].update(token.encode("utf-8") + b"\n")

    table_hash_short = short_hash_from_hasher(table_hasher, hex_digits=4)
    column_hashes_short = {
        name: short_hash_from_hasher(h, hex_digits=4)
        for name, h in col_hashers.items()
    }
    return table_hash_short, column_hashes_short


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?;
        """,
        (table_name,),
    )
    return cur.fetchone() is not None


def table_has_column(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    cur = conn.cursor()
    try:
        cur.execute(f"PRAGMA table_info({table_name});")
    except sqlite3.OperationalError:
        return False
    cols = [r["name"] for r in cur.fetchall()]
    return column_name in cols


def get_high_level_counts(conn: sqlite3.Connection) -> Dict[str, Optional[int]]:
    """
    Returns:
        volumes_count
        directories_count
        files_count
        files_present_count
        files_system_count
        files_symlink_count
    """
    cur = conn.cursor()
    result: Dict[str, Optional[int]] = {
        "volumes_count": None,
        "directories_count": None,
        "files_count": None,
        "files_present_count": None,
        "files_system_count": None,
        "files_symlink_count": None,
    }

    if table_exists(conn, "volumes"):
        cur.execute("SELECT COUNT(*) AS c FROM volumes;")
        row = cur.fetchone()
        result["volumes_count"] = int(row["c"]) if row is not None else 0

    if table_exists(conn, "directories"):
        cur.execute("SELECT COUNT(*) AS c FROM directories;")
        row = cur.fetchone()
        result["directories_count"] = int(row["c"]) if row is not None else 0

    if table_exists(conn, "files"):
        cur.execute("SELECT COUNT(*) AS c FROM files;")
        row = cur.fetchone()
        result["files_count"] = int(row["c"]) if row is not None else 0

        if table_has_column(conn, "files", "presence_state"):
            cur.execute(
                "SELECT COUNT(*) AS c FROM files WHERE presence_state = 0;"
            )
            row = cur.fetchone()
            result["files_present_count"] = int(row["c"]) if row is not None else 0

        if table_has_column(conn, "files", "system"):
            cur.execute(
                "SELECT COUNT(*) AS c FROM files WHERE system = 1;"
            )
            row = cur.fetchone()
            result["files_system_count"] = int(row["c"]) if row is not None else 0

        if table_has_column(conn, "files", "is_symlink"):
            cur.execute(
                "SELECT COUNT(*) AS c FROM files WHERE is_symlink = 1;"
            )
            row = cur.fetchone()
            result["files_symlink_count"] = int(row["c"]) if row is not None else 0

    return result


def summarize_database(db_path: Path) -> None:
    if not db_path.exists():
        print(f"ERROR: Database file not found: {db_path}")
        return

    print(f"Database path: {db_path}")
    size = get_file_size(db_path)
    print(f"File size: {size} bytes")

    db_hash_short = short_hash_file(db_path)
    print(f"Database file short hash (16-bit): {db_hash_short}")
    print()

    conn = get_connection(db_path)
    try:
        table_names = get_table_names(conn)
        if not table_names:
            print("No user tables found in this database.")
            return

        print("Tables found:")
        for name in table_names:
            print(f"  - {name}")
        print()

        for table_name in table_names:
            print(f"=== Table: {table_name} ===")
            n_rows, n_cols, col_names = get_table_dimensions_and_columns(conn, table_name)
            print(f"  Rows:    {n_rows}")
            print(f"  Columns: {n_cols}")
            print(f"  Column names: {', '.join(col_names) if col_names else '(none)'}")
            print("  Computing 16-bit table and column hashes...")
            table_hash, column_hashes = hash_table_and_columns(conn, table_name)
            print(f"  Table short hash: {table_hash}")
            print("  Column short hashes:")
            for col_name in col_names:
                ch = column_hashes.get(col_name, "(none)")
                print(f"    {col_name}: {ch}")
            print()

        counts = get_high_level_counts(conn)
        print("=== Overall summary ===")
        if counts["volumes_count"] is not None:
            print(f"Volumes:                 {counts['volumes_count']}")
        else:
            print("Volumes:                 (no 'volumes' table)")

        if counts["directories_count"] is not None:
            print(f"Directories:             {counts['directories_count']}")
        else:
            print("Directories:             (no 'directories' table)")

        if counts["files_count"] is not None:
            print(f"Files (all rows):        {counts['files_count']}")
        else:
            print("Files (all rows):        (no 'files' table)")

        if counts["files_present_count"] is not None:
            print(f"Files present:           {counts['files_present_count']}")
        else:
            print("Files present:           (presence_state column missing)")

        print()
        print("Special files:")
        if counts["files_system_count"] is not None:
            print(f"  System (system=1):          {counts['files_system_count']}")
        else:
            print("  System (system=1):          (system column missing)")

        if counts["files_symlink_count"] is not None:
            print(f"  Symlinks (is_symlink=1):    {counts['files_symlink_count']}")
        else:
            print("  Symlinks (is_symlink=1):    (is_symlink column missing)")

        print()

    finally:
        conn.close()


if __name__ == "__main__":
    db_path = get_db_path_from_args(sys.argv)
    summarize_database(db_path)
