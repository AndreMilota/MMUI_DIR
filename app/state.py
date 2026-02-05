"""State shared between nodes in the LangGraph database query workflow.

This TypedDict defines what flows through the graph as we convert natural
language queries into SQL and execute them against the file_scan database.
"""
from typing import TypedDict, Optional, List, Dict, Any

class State(TypedDict, total=False):
    # Input: natural language query from user
    user_text: str                      # e.g., "Show me all mp3 files in Music folder"

    # SQL generation
    sql: Optional[str]                  # Generated SQL query
    sql_params: Optional[Dict[str, Any]]  # Parameters for parameterized queries

    # Query results
    results: Optional[List[Dict[str, Any]]]  # Rows returned from the database
    error: Optional[str]                # Error message if query fails

    # Natural language response
    response: Optional[str]             # LLM-generated response to user

    # Current time (for relative-time queries)
    now_ns: Optional[int]               # Current time as nanoseconds since Unix epoch
    now_iso: Optional[str]              # Current time as ISO-8601 string

    # Database override
    db_path: Optional[str]              # Path to SQLite database (default: auto-discovered)
