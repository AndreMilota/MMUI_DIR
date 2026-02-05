"""
export_db.py

Export the SQLite tables from file_database.sqlite into tab-delimited
text files that you can open in Excel or other spreadsheet programs.

By default, it exports:
    - volumes.tsv
    - directories.tsv
    - files.tsv

Timestamps (columns ending in ``_ns``) are converted to human-readable
strings by default.  Pass ``--raw-timestamps`` to keep the raw nanosecond
integers instead.

Usage (no args, defaults to 'file_database.sqlite' in the project):
    python export_db.py

Or explicitly:
    python export_db.py path/to/file_database.sqlite

Raw nanosecond output:
    python export_db.py --raw-timestamps
"""

import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable


def _ns_to_str(ns_value):
    """Convert nanoseconds since epoch to a human-readable string."""
    if ns_value is None:
        return None
    try:
        seconds = ns_value / 1_000_000_000
        return datetime.fromtimestamp(seconds).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, OverflowError, ValueError):
        return ns_value


def export_table_to_tsv(
    conn: sqlite3.Connection,
    table_name: str,
    out_path: Path,
    raw_timestamps: bool = False,
) -> None:
    """
    Export a single table to a tab-delimited file with a header row.

    Args:
        conn: Open SQLite connection.
        table_name: Name of the table to export.
        out_path: Destination .tsv file path.
        raw_timestamps: If False (default), columns whose names end with
            ``_ns`` are converted from nanoseconds to human-readable
            datetime strings.  If True, the raw integer values are kept.
    """
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table_name};")

    # Column names from cursor.description
    column_names = [desc[0] for desc in cur.description]

    # Identify which column indices hold nanosecond timestamps
    ns_columns = set()
    if not raw_timestamps:
        ns_columns = {i for i, name in enumerate(column_names) if name.endswith("_ns")}

    # Strip the _ns suffix from headers when displaying human-readable times
    if ns_columns:
        header = [
            name[:-3] if i in ns_columns else name
            for i, name in enumerate(column_names)
        ]
    else:
        header = column_names

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(header)
        for row in cur:
            if ns_columns:
                out_row = [
                    _ns_to_str(val) if i in ns_columns else val
                    for i, val in enumerate(row)
                ]
            else:
                out_row = list(row)
            writer.writerow(out_row)

    print(f"Exported {table_name} -> {out_path}")


def export_all_tables(
    db_path: Path,
    out_dir: Path,
    tables: Iterable[str],
    raw_timestamps: bool = False,
) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        for table in tables:
            out_file = out_dir / f"{table}.tsv"
            export_table_to_tsv(conn, table, out_file, raw_timestamps=raw_timestamps)
    finally:
        conn.close()


if __name__ == "__main__":
    # Default DB: file_database.sqlite in the project directory (same folder as this script)
    script_dir = Path(__file__).resolve().parent
    default_db = script_dir / "../file_database.sqlite"

    # Parse args: [db_path] [--raw-timestamps]
    args = sys.argv[1:]
    raw_timestamps = False
    if "--raw-timestamps" in args:
        raw_timestamps = True
        args.remove("--raw-timestamps")

    if args:
        db_path = Path(args[0])
    else:
        db_path = default_db

    if not db_path.exists():
        print(f"Database file not found: {db_path}")
        sys.exit(1)

    # Export into the same directory as the DB (you can change this if you like)
    out_dir = db_path.parent

    print(f"Exporting tables from {db_path} into {out_dir} ...")
    if raw_timestamps:
        print("(using raw nanosecond timestamps)")
    export_all_tables(db_path, out_dir, tables=["volumes", "directories", "files"],
                      raw_timestamps=raw_timestamps)
    print("Done.")
