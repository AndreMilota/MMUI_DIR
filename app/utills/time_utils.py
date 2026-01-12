# python
# app/utills/time_utils.py
from datetime import datetime, timezone
import time

def parse_human_time(now_str: str) -> datetime:
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

def now_ns_and_iso_from_dt(dt: datetime):
    """Normalize datetime to (now_ns, now_iso) with UTC Z suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_utc = dt.astimezone(timezone.utc)
    ns = int(dt_utc.timestamp() * 1e9)
    iso = dt_utc.isoformat().replace("+00:00", "Z")
    return ns, iso