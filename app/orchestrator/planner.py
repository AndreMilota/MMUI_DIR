"""Planner node: read user_text and produce a tiny plan dict.

Right now we use simple rules:
- "ui: ..."    -> mode "ui"
- "data: ..."  -> mode "data"
- "agent: ..." -> mode "agent"
Fallback to previous demo modes (show_covers, write_sql, answer).
"""
from typing import Dict, Any

def plan(user_text: str) -> Dict[str, Any]:
    text = (user_text or "").strip()
    lower = text.lower()

    # Prefix routing (explicit commands)
    for prefix, mode in (("ui:", "ui"), ("data:", "data"), ("agent:", "agent")):
        if lower.startswith(prefix):
            remainder = text[len(prefix):].strip()
            return {"mode": mode, "args": {"command": remainder}}

    # Demo routes from earlier scaffolding
    if "cover" in lower or "album" in lower:
        return {"mode": "show_covers", "args": {"time_window": "last_8_months", "filetype": "mp3"}}
    if "sql" in lower:
        return {"mode": "write_sql", "args": {}}

    # Default
    return {"mode": "answer", "args": {}}
