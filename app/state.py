"""Project state shared between nodes in LangGraph.

We start with a simple TypedDict. Later, we can switch to Pydantic models
if we want validation.
"""
from typing import TypedDict, Optional, List, Dict, Any

class State(TypedDict, total=False):
    # Input from the user (or UI)
    user_text: str                      # last user request in natural language

    # Planning (we will fill these in when we add the planner)
    mode: str                           # e.g., "answer", "write_sql", "show_covers"
    plan: Dict[str, Any]                # tiny plan JSON from the planner node

    # SQL path (summary and results)
    sql: Optional[str]                  # last SQL proposed by the model
    sql_params: Dict[str, Any]          # parameters for that SQL
    preview: List[Dict[str, Any]]       # small preview rows
    results: List[Dict[str, Any]]       # final rows or items for the user
