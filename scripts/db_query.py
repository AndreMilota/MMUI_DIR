# scripts/db_query.py
from app.tools.sql import query

rows = query(
    "SELECT id, path, acquired_ts FROM files ORDER BY id LIMIT :n",
    {"n": 5}
)
for r in rows:
    print(r)
