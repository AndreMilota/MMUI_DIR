# app/runner.py
"""Entry point for running natural language queries against the file_scan database."""
from typing import Dict, Any

# TODO: Import once graph is built
# from app.graph import build_app

def run_query(user_text: str) -> Dict[str, Any]:
    """
    Run a natural language query against the file_scan database.

    Args:
        user_text: Natural language query (e.g., "Show me all mp3 files")

    Returns:
        Dictionary with 'sql', 'results', and optionally 'error'
    """
    # TODO: Uncomment once graph is implemented
    # app = build_app()
    # state_out = app.invoke({"user_text": user_text})
    # return {
    #     "sql": state_out.get("sql"),
    #     "results": state_out.get("results"),
    #     "error": state_out.get("error"),
    # }

    return {
        "sql": None,
        "results": None,
        "error": "Graph not yet implemented"
    }
