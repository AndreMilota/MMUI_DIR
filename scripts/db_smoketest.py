# scripts/db_smoketest.py
from pathlib import Path
import sqlite3
from datetime import datetime

DB_PATH = Path("db") / "files.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def connect():
    return sqlite3.connect(DB_PATH)

def setup():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL,
                acquired_ts TEXT
            )
        """)

def seed_if_empty():
    with connect() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM files")
        (count,) = cur.fetchone()
        if count == 0:
            now = datetime.now().isoformat(timespec="seconds")
            conn.executemany(
                "INSERT INTO files(path, acquired_ts) VALUES(?, ?)",
                [
                    (r"C:\Music\Sample1.mp3", now),
                    (r"C:\Music\Sub\Sample2.mp3", now),
                ],
            )

def read_some():
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, path, acquired_ts FROM files ORDER BY id LIMIT 5"
        ).fetchall()
        for row in rows:
            print(dict(zip(["id", "path", "acquired_ts"], row)))

if __name__ == "__main__":
    setup()
    seed_if_empty()
    read_some()
