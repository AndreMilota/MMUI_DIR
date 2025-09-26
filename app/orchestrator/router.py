# app/orchestrator/router.py
"""Map planner 'mode' → graph node name."""

def route(mode: str) -> str:
    mapping = {
        # primary modes
        "ui_control": "UI",
        "data_query": "Data",
        "agent": "Agent",

        # optional legacy demo modes (safe to keep or remove)
        "write_sql": "SqlSummary",
        "show_covers": "CoversSummary",
    }
    return mapping.get(mode, "Agent")  # default fallback
