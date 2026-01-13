# python
# app/utils/time_utils.py
from datetime import datetime, timezone

from datetime import datetime, timezone
import time
from typing import Optional, Tuple, Union
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Iterable, List, Optional



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

# fields to consider as timestamps (common names used in the project)
_TIMESTAMP_FIELDS = {"mtime_ns", "acquired_ts", "acquired_ts_ns", "created_ts", "mtime", "timestamp", "ts"}

def ns_from_value(v: Any) -> Optional[int]:
    """Try to interpret a value as nanoseconds since epoch.
    - If integer and large (> 1e12) assume nanoseconds.
    - If integer and small (<= 1e12) assume seconds and convert to ns.
    - If float treat as seconds and convert.
    - Otherwise return None.
    """
    try:
        if isinstance(v, int):
            if abs(v) > 1_000_000_000_000:  # > ~2001-09-09 in seconds -> treat as ns
                return int(v)
            else:
                return int(v * 1_000_000_000)
        if isinstance(v, float):
            return int(v * 1_000_000_000)
        if isinstance(v, str) and v.isdigit():
            # numeric-string: decide by length
            if len(v) > 12:
                return int(v)
            else:
                return int(int(v) * 1_000_000_000)
    except Exception:
        pass
    return None

def ns_to_iso(ns: int) -> str:
    dt = datetime.fromtimestamp(ns / 1e9, tz=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")

def ns_to_relative(ns: int, now_ns: int) -> str:
    # simple human-friendly relative description (approx)
    delta_ns = now_ns - ns
    if delta_ns == 0:
        return "now"
    future = delta_ns < 0
    delta = abs(delta_ns) / 1e9
    if delta < 60:
        v = int(delta)
        unit = "second" if v == 1 else "seconds"
    elif delta < 3600:
        v = int(delta / 60)
        unit = "minute" if v == 1 else "minutes"
    elif delta < 86400:
        v = int(delta / 3600)
        unit = "hour" if v == 1 else "hours"
    else:
        v = int(delta / 86400)
        unit = "day" if v == 1 else "days"
    return f"in {v} {unit}" if future else f"{v} {unit} ago"

def row_to_dict(row: Any) -> Dict[str, Any]:
    """Convert a DB row to a plain dict (works for sqlite3.Row, dict, tuple)."""
    if isinstance(row, dict):
        return dict(row)
    try:
        # sqlite3.Row supports mapping protocol
        return dict(row)
    except Exception:
        pass
    # fallback for tuple: return indexed keys
    try:
        return {str(i): v for i, v in enumerate(row)}
    except Exception:
        return {"value": row}

def format_timestamps_in_row(row: Dict[str, Any], now_ns: Optional[int]) -> Dict[str, Any]:
    """Return a copy of row with timestamp fields replaced by 'ISO (relative)' strings."""
    out = {}
    for k, v in row.items():
        if k in _TIMESTAMP_FIELDS:
            ns = ns_from_value(v)
            if ns is not None:
                iso = ns_to_iso(ns)
                rel = ns_to_relative(ns, now_ns) if now_ns is not None else None
                out[k] = f"{iso}" + (f" ({rel})" if rel else "")
                continue
        out[k] = v
    return out


def compute_time_boundaries(now_ns: int) -> dict:
    """
    Compute human-friendly and nanosecond boundaries for common periods
    based on the provided `now_ns` (UTC).

    Returns dict with keys:
      - start_of_day_iso, start_of_day_ns
      - start_of_next_day_iso, start_of_next_day_ns
      - start_of_week_iso, start_of_week_ns          # week starts Monday UTC
      - start_of_next_week_iso, start_of_next_week_ns
      - start_of_month_iso, start_of_month_ns
      - start_of_next_month_iso, start_of_next_month_ns
    """
    dt = datetime.fromtimestamp(now_ns / 1e9, tz=timezone.utc)
    # start of day
    sod = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    sod_next = sod + timedelta(days=1)

    # start of week (Monday)
    sow = (sod - timedelta(days=dt.weekday()))
    sow_next = sow + timedelta(days=7)

    # start of month
    som = sod.replace(day=1)
    # next month: increment month safely
    if som.month == 12:
        som_next = som.replace(year=som.year + 1, month=1)
    else:
        som_next = som.replace(month=som.month + 1)

    def to_ns_iso(dt_obj: datetime):
        ns = int(dt_obj.timestamp() * 1e9)
        iso = dt_obj.isoformat().replace("+00:00", "Z")
        return ns, iso

    sod_ns, sod_iso = to_ns_iso(sod)
    sodn_ns, sodn_iso = to_ns_iso(sod_next)
    sow_ns, sow_iso = to_ns_iso(sow)
    sown_ns, sown_iso = to_ns_iso(sow_next)
    som_ns, som_iso = to_ns_iso(som)
    somn_ns, somn_iso = to_ns_iso(som_next)

    return {
        "start_of_day_ns": sod_ns,
        "start_of_day_iso": sod_iso,
        "start_of_next_day_ns": sodn_ns,
        "start_of_next_day_iso": sodn_iso,
        "start_of_week_ns": sow_ns,
        "start_of_week_iso": sow_iso,
        "start_of_next_week_ns": sown_ns,
        "start_of_next_week_iso": sown_iso,
        "start_of_month_ns": som_ns,
        "start_of_month_iso": som_iso,
        "start_of_next_month_ns": somn_ns,
        "start_of_next_month_iso": somn_iso,
    }

def _dt_to_ns_iso(dt: datetime) -> Tuple[int, str]:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_utc = dt.astimezone(timezone.utc)
    ns = int(dt_utc.timestamp() * 1e9)
    iso = dt_utc.isoformat().replace("+00:00", "Z")
    return ns, iso

def get_now_ns_and_iso(
    value: Optional[Union[int, float, str, datetime]] = None
) -> Tuple[int, str]:
    """
    Return (now_ns, now_iso) normalized to UTC.

    Accepts:
      - None: use system clock
      - int: treated as ns if > 1e12, otherwise seconds
      - float: seconds
      - str: ISO8601, numeric (seconds or ns), or common formats like
             '%Y-%m-%d %H:%M:%S' or '%Y-%m-%d'
      - datetime: used (naive treated as UTC)

    Raises ValueError for unrecognized string formats.
    """
    if value is None:
        ns = time.time_ns()
        iso = datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        return ns, iso

    # int
    if isinstance(value, int):
        if abs(value) > 1_000_000_000_000:  # treat as ns
            return int(value), datetime.fromtimestamp(value / 1e9, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        else:  # seconds
            ns = int(value * 1e9)
            return ns, datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).isoformat().replace("+00:00", "Z")

    # float -> seconds
    if isinstance(value, float):
        ns = int(value * 1e9)
        return ns, datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).isoformat().replace("+00:00", "Z")

    # datetime
    if isinstance(value, datetime):
        return _dt_to_ns_iso(value)

    # str
    if isinstance(value, str):
        s = value.strip()
        # numeric string
        if s.isdigit():
            if len(s) > 12:
                ns = int(s)
                return ns, datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).isoformat().replace("+00:00", "Z")
            else:
                ns = int(int(s) * 1e9)
                return ns, datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        # ISO-like
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return _dt_to_ns_iso(dt)
        except Exception:
            pass
        # common strptime patterns
        patterns = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"]
        for fmt in patterns:
            try:
                dt = datetime.strptime(s, fmt)
                dt = dt.replace(tzinfo=timezone.utc)
                return _dt_to_ns_iso(dt)
            except Exception:
                continue

    raise ValueError(f"Unrecognized time value: {value!r}")