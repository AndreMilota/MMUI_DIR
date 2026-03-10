# app/graph.py
"""LangGraph workflow for natural language database queries.

Flow: user_text → SQL → execute → results → natural language response
"""
import sqlite3
from pathlib import Path
from langgraph.graph import StateGraph, END
from app.state import State
from app.llm.core import chat
from file_scan.fs_database import LLM_DB_SCHEMA_DOC
from app.utils.time_utils import format_timestamps_in_row, compute_time_boundaries, get_now_ns_and_iso
from typing import Any, Dict, Iterable, List, Optional

# python
def locate_db(filename="file_database.sqlite", folder="file_scan", max_levels=8):
    """Search upward from cwd and this file's directory for folder/filename."""
    starts = [Path.cwd(), Path(__file__).resolve().parent]
    for start in starts:
        p = start
        for _ in range(max_levels + 1):
            candidate = p / folder / filename
            if candidate.exists():
                return candidate.resolve()
            if p.parent == p:
                break
            p = p.parent
    # fallback to relative path (may be used when packaging)
    fallback = Path(folder) / filename
    return fallback.resolve() if fallback.exists() else fallback

DB_PATH = locate_db()
# removed `current_directory` - not needed

def text_to_sql(state: State) -> State:
    user_text = state.get("user_text", "")
    now_ns = state.get("now_ns")
    now_iso = state.get("now_iso")
    now_ns, now_iso = state["now_ns"], state["now_iso"]

    bounds = compute_time_boundaries(now_ns)

    # Provide explicit instructions and current time + period boundaries to the LLM
    system_prompt = f"""You are a SQL query generator for a file management database.

Current time (UTC): {now_iso}
Current time (nanoseconds since epoch): {now_ns}

Period boundaries (UTC / ns):
timedelta- start_of_day: {bounds['start_of_day_iso']} (ns={bounds['start_of_day_ns']})
- start_of_next_day: {bounds['start_of_next_day_iso']} (ns={bounds['start_of_next_day_ns']})
- start_of_week: {bounds['start_of_week_iso']} (ns={bounds['start_of_week_ns']})
- start_of_next_week: {bounds['start_of_next_week_iso']} (ns={bounds['start_of_next_week_ns']})
- start_of_month: {bounds['start_of_month_iso']} (ns={bounds['start_of_month_ns']})
- start_of_next_month: {bounds['start_of_next_month_iso']} (ns={bounds['start_of_next_month_ns']})

When the user says phrases like "this week", "last week", "this month", or "today":
- Use the provided period boundaries to build SQL comparisons on `mtime_ns`.
- Example for "this week": `WHERE presence_state = 0 AND mtime_ns >= {bounds['start_of_week_ns']} AND mtime_ns < {bounds['start_of_next_week_ns']}`.
- Example for "today": `WHERE presence_state = 0 AND mtime_ns >= {bounds['start_of_day_ns']} AND mtime_ns < {bounds['start_of_next_day_ns']}`.

When converting relative durations (e.g. "older than 7 days"), you may use arithmetic with `now_ns` (provided above).
Current time (ISO): {now_iso}
Current time (nanoseconds since epoch): {now_ns}

{LLM_DB_SCHEMA_DOC}

Your task:
1. Read the user's natural language query
2. Generate a valid SQLite query that answers their question
3. Return ONLY the SQL query, nothing else - no explanations, no markdown, no extra text

Important:
- Use proper JOINs between files, directories, and volumes tables
- Full file paths are: directories.dir_path || '/' || files.name || '.' || files.extension
- Filter for presence_state = 0 (PRESENT files) unless user asks for historical data
- NEVER use strftime('%s','now') or date('now') — always use the literal now_ns value above for time arithmetic
- ctime_ns is creation time; mtime_ns is last-modification time. When the user says "created", "added", or "old" use ctime_ns. When the user says "modified" or "changed" use mtime_ns
- For relative time calculations, compare directly against nanosecond values. For example "older than 7 days" means ctime_ns < {now_ns} - 7*86400*1000000000
- Be careful with NULL values in optional fields
"""
    user_prompt = f"Generate SQL for this query: {user_text}"

    sql = chat(system_prompt, user_prompt, temperature=0.0)
    sql = sql.strip().strip('`').strip()
    if sql.lower().startswith('sql\n'):
        sql = sql[4:].strip()

    state["sql"] = sql
    return state

def execute_sql(state: State) -> State:
    """Node 2: Execute the SQL query against the file_scan database."""
    sql = state.get("sql")

    if not sql:
        state["error"] = "No SQL query generated"
        state["results"] = []
        return state

    try:
        conn = sqlite3.connect(state.get("db_path") or DB_PATH)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()

        cursor.execute(sql)
        rows = cursor.fetchall()

        # Convert Row objects to dictionaries
        results = [dict(row) for row in rows]

        conn.close()

        state["results"] = results
        state["error"] = None

    except Exception as e:
        state["error"] = f"SQL execution error: {str(e)}"
        state["results"] = []

    return state

def _row_to_dict(row: Any) -> Dict[str, Any]:
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

def sql_to_text(state: Dict) -> Dict:
    """
    Convert SQL results in state['results'] (or state['rows']) into an LLM prompt.
    Expects `state['now_ns']` (int) if you want relative times. Does not call OS time.
    """
    now_ns = state.get("now_ns")  # must be provided by run_query/runner if relative strings needed
    now_iso = state.get("now_iso")

    rows_source = state.get("results") or state.get("rows") or state.get("sql_results") or []
    rows: List[Dict[str, Any]] = []
    for r in rows_source:
        d = _row_to_dict(r)
        d_fmt = format_timestamps_in_row(d, now_ns)
        rows.append(d_fmt)

    # Build a compact textual representation to feed the LLM.
    # This keeps the LLM from needing to convert large integers itself.
    lines = []
    for i, r in enumerate(rows, start=1):
        pairs = [f"{k}={v}" for k, v in r.items()]
        lines.append(f"{i}: " + ", ".join(pairs))

    current_time_line = f"Current time (from runner): {now_iso}" if now_iso else "Current time: not provided"
    system_prompt = (
        "You are a natural-language summarizer for SQL query results.\n"
        f"{current_time_line}\n"
        "Rows:\n"
        + "\n".join(lines)
        + "\n\n"
        "Produce a short natural-language answer that summarizes or answers the user's request, "
        "using the human-readable timestamps shown above. Return only the text answer."
    )

    user_text = state.get("user_text", "")
    # call the chat/LLM function (assumes a `chat` function exists in the module)
    answer = chat(system_prompt, user_text, temperature=0.0)
    state["response"] = answer.strip()
    return state


def build_app():
    """Build and compile the LangGraph workflow."""
    graph = StateGraph(State)

    # Add the three nodes
    graph.add_node("text_to_sql", text_to_sql)
    graph.add_node("execute_sql", execute_sql)
    graph.add_node("sql_to_text", sql_to_text)

    # Define the flow: text_to_sql → execute_sql → sql_to_text → END
    graph.set_entry_point("text_to_sql")
    graph.add_edge("text_to_sql", "execute_sql")
    graph.add_edge("execute_sql", "sql_to_text")
    graph.add_edge("sql_to_text", END)

    return graph.compile()
