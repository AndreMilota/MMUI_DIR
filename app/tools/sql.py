# app/tools/sql.py
import sqlite3
from pathlib import Path
from typing import Iterable, Any, List, Dict


def get_db_connection():
    # Path to the database file relative to project root
    db_path = Path(__file__).resolve().parents[2] / 'db' / 'files.db'
    # Ensure the db directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(db_path))

def query(sql: str, params: Iterable[Any] | Dict[str, Any] = ()) -> List[Dict[str, Any]]:
    """Run a read-only SELECT and return a list of dictionaries."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    rows = cursor.fetchall()
    conn.close()
    return rows

def execute(sql: str, params: Iterable[Any] | Dict[str, Any] = ()) -> int:
    """Run an INSERT/UPDATE/DELETE and return the number of affected rows."""
    with get_db_connection() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.rowcount
