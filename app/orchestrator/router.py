"""Router: map the chosen mode to the next node name."""

def route(mode: str) -> str:
    # New subgraphs
    if mode == "ui":
        return "UI"
    if mode == "data":
        return "Data"
    if mode == "agent":
        return "Agent"

    # Older demo modes we kept
    if mode == "write_sql":
        return "SqlSummary"
    if mode == "show_covers":
        return "CoversSummary"

    return "Answer"
