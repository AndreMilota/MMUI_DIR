# scripts/db_query.py
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tools.sql import query

rows = query(
    "SELECT id, path, created_at FROM files ORDER BY id LIMIT :n",
    {"n": 5}
)
for r in rows:
    print(r)
