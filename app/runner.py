# python
# app/runner.py
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import time

from app.graph import build_app
from app.utils.time_utils import parse_human_time, now_ns_and_iso_from_dt


def run_query(user_text: str, now: Optional[str] = None) -> Dict[str, Any]:
    """
    Run a natural language query against the file_scan database.

    Args:
        user_text: Natural language query (e.g., "Show me all mp3 files")
        now: Optional human-readable time string. If provided it will be used
             as the current time for relative-time queries. If omitted the
             system clock is used and a message is printed.

    Returns:
        Dictionary with 'sql', 'results', 'response', and optionally 'error'
    """
    app = build_app()

    # determine now_ns / now_iso
    if now is None:
        # use system time
        ns = time.time_ns()
        iso = datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        print(f"Using system time: {iso}")
    else:
        try:
            dt = parse_human_time(now)
            ns, iso = now_ns_and_iso_from_dt(dt)
            print(f"Using provided time: {iso}")
        except Exception as exc:
            # fallback to system time if parsing fails
            print(f"Warning: failed to parse provided time ({exc}). Falling back to system time.")
            ns = time.time_ns()
            iso = datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).isoformat().replace("+00:00", "Z")

    state_in = {
        "user_text": user_text,
        "now_ns": ns,
        "now_iso": iso,
    }

    state_out = app.invoke(state_in)

    return {
        "sql": state_out.get("sql"),
        "results": state_out.get("results"),
        "response": state_out.get("response"),
        "error": state_out.get("error"),
    }
