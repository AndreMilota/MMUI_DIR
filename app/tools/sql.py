# app/tools/sql.py
from pathlib import Path
import sqlite3
from typing import Iterable, Any, List, Dict

# Always anchor paths at the project root, not the working directory.
# This file lives at app/tools/sql.py, so parents[2] is the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "db" / "files.db"

def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def query(sql: str, params: Iterable[Any] | Dict[str, Any] = ()) -> List[Dict[str, Any]]:
    """Run a read-only SELECT and return a list of dictionaries."""
    with connect() as conn:
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

def execute(sql: str, params: Iterable[Any] | Dict[str, Any] = ()) -> int:
    """Run an INSERT/UPDATE/DELETE and return the number of affected rows."""
    with connect() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.rowcount
