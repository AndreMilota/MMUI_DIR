# python
# app/runner.py
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import time

from app.graph import build_app

def _parse_human_time(now_str: str) -> datetime:
    """Try to parse common human-readable time formats into a timezone-aware UTC datetime.

    Accepted forms:
    - ISO8601 (with or without trailing Z)
    - 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'
    - numeric timestamps: seconds (e.g. '1672531200') or nanoseconds (e.g. '1672531200000000000')
    """
    s = now_str.strip()
    # numeric: treat long numbers as ns, short as seconds
    if s.isdigit():
        if len(s) > 12:
            # nanoseconds
            ns = int(s)
            return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc)
        else:
            # seconds
            ts = int(s)
            return datetime.fromtimestamp(ts, tz=timezone.utc)

    # ISO-like
    try:
        # accept trailing Z as UTC
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        pass

    # try common strptime patterns
    patterns = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"]
    for fmt in patterns:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue

    raise ValueError(f"Unrecognized time format: {now_str}")

def _now_ns_and_iso_from_dt(dt: datetime):
    """Normalize datetime to (now_ns, now_iso) with UTC Z suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_utc = dt.astimezone(timezone.utc)
    ns = int(dt_utc.timestamp() * 1e9)
    iso = dt_utc.isoformat().replace("+00:00", "Z")
    return ns, iso

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
            dt = _parse_human_time(now)
            ns, iso = _now_ns_and_iso_from_dt(dt)
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
