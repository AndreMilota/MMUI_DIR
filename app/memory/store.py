# app/memory/store.py
from __future__ import annotations
from pathlib import Path
import json
from typing import Dict, Any

# Store one small JSON blob per session id under db/memory/
MEM_DIR = Path("db") / "memory"
MEM_DIR.mkdir(parents=True, exist_ok=True)

def _path(session_id: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
    return MEM_DIR / f"{safe}.json"

def load(session_id: str) -> Dict[str, Any]:
    p = _path(session_id)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save(session_id: str, data: Dict[str, Any]) -> None:
    p = _path(session_id)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def merge(session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    cur = load(session_id)
    for k, v in updates.items():
        if v is not None:
            cur[k] = v
    save(session_id, cur)
    return cur
