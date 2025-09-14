"""Planner node: read user_text and produce a tiny plan dict.

Later we will call your model here. For now, we return a simple
rule-based plan so the graph can run end-to-end.
"""

from typing import Dict, Any

def plan(user_text: str) -> Dict[str, Any]:
    text = (user_text or "").lower()

    # Very small rules to prove the wiring works.
    if "cover" in text or "album" in text:
        return {"mode": "show_covers", "args": {"time_window": "last_8_months", "filetype": "mp3"}}
    if "sql" in text:
        return {"mode": "write_sql", "args": {}}

    # Default: just answer in plain English.
    return {"mode": "answer", "args": {}}
