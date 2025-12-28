"""
export_db.py

Export the SQLite tables from file_database.sqlite into tab-delimited
text files that you can open in Excel or other spreadsheet programs.

By default, it exports:
    - volumes.tsv
    - directories.tsv
    - files.tsv

Usage (no args, defaults to 'file_database.sqlite' in the project):
    python export_db.py

Or explicitly:
    python export_db.py path/to/file_database.sqlite
"""

import csv
import sqlite3
import sys
from pathlib import Path
from typing import Iterable


def export_table_to_tsv(conn: sqlite3.Connection, table_name: str, out_path: Path) -> None:
    """
    Export a single table to a tab-delimited file with a header row.
    """
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table_name};")

    # Column names from cursor.description
    column_names = [desc[0] for desc in cur.description]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(column_names)
        for row in cur:
            # row is a tuple; if the connection used row_factory, cast to tuple explicitly
            writer.writerow(list(row))

    print(f"Exported {table_name} -> {out_path}")


def export_all_tables(db_path: Path, out_dir: Path, tables: Iterable[str]) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        for table in tables:
            out_file = out_dir / f"{table}.tsv"
            export_table_to_tsv(conn, table, out_file)
    finally:
        conn.close()


if __name__ == "__main__":
    # Default DB: file_database.sqlite in the project directory (same folder as this script)
    script_dir = Path(__file__).resolve().parent
    default_db = script_dir / "../file_database.sqlite"

    if len(sys.argv) >= 2:
        db_path = Path(sys.argv[1])
    else:
        db_path = default_db

    if not db_path.exists():
        print(f"Database file not found: {db_path}")
        sys.exit(1)

    # Export into the same directory as the DB (you can change this if you like)
    out_dir = db_path.parent

    print(f"Exporting tables from {db_path} into {out_dir} ...")
    export_all_tables(db_path, out_dir, tables=["volumes", "directories", "files"])
    print("Done.")
