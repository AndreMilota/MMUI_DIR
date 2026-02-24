# app_2/runner.py
"""
Entry point for running queries through the branching LangGraph workflow.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import time

from app_2.graph import build_app
from app.utills.time_utils import parse_human_time, now_ns_and_iso_from_dt
from app.utils.clipboard import print_copy


def run_query(
    user_input: str,
    now: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run a natural language query through the branching workflow.

    Args:
        user_input: Natural language query/command from user
        now: Optional human-readable time string for relative-time queries.
             If omitted, system clock is used.
        db_path: Optional path to SQLite database. If omitted, auto-discovered.

    Returns:
        Dictionary with execution results including:
        - action_type: The classified action type
        - sql: Generated SQL (if any)
        - query_result: Raw query results (if any)
        - final_response: Natural language response
        - stored_table: Stored table for multi-turn (if any)
        - error: Error message (if any)
    """
    app = build_app()

    # Determine now_ns / now_iso
    if now is None:
        ns = time.time_ns()
        iso = datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        print(f"Using system time: {iso}")
    else:
        try:
            dt = parse_human_time(now)
            ns, iso = now_ns_and_iso_from_dt(dt)
            print(f"Using provided time: {iso}")
        except Exception as exc:
            print(f"Warning: failed to parse provided time ({exc}). Falling back to system time.")
            ns = time.time_ns()
            iso = datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).isoformat().replace("+00:00", "Z")

    # Build initial state
    state_in = {
        "user_input": user_input,
        "now_ns": ns,
        "now_iso": iso,
    }
    if db_path is not None:
        state_in["db_path"] = db_path

    # Print user request to clipboard for accessibility
    print_copy(f"User request: {user_input}")

    # Run the graph
    state_out = app.invoke(state_in)

    # Extract execution plan details
    plan = state_out.get("execution_plan")

    # Print and copy the response for accessibility
    print_copy(f"Response: {state_out.get('final_response')}")

    return {
        "action_type": plan.action_type.value if plan else None,
        "sql": state_out.get("sql"),
        "query_result": state_out.get("query_result"),
        "final_response": state_out.get("final_response"),
        "stored_table": state_out.get("stored_table"),
        "stored_table_description": state_out.get("stored_table_description"),
        "query_error": state_out.get("query_error"),
        "reasoning": plan.reasoning if plan else None,
    }