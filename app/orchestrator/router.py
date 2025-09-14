"""Router: map the chosen mode to the next node name."""

def route(mode: str) -> str:
    # These names must match the node names we add in graph.py
    if mode == "write_sql":
        return "SqlSummary"
    if mode == "show_covers":
        return "CoversSummary"
    return "Answer"
