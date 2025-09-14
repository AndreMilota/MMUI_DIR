"""Wire the graph: Entry -> Planner -> (branch based on mode) -> END."""
from langgraph.graph import StateGraph, END
from app.state import State
from app.orchestrator.planner import plan
from app.orchestrator.router import route

def entry(state: State) -> State:
    # Expect state["user_text"] to be present
    return state

def planner_node(state: State) -> State:
    # Produce a tiny plan and record the mode
    p = plan(state.get("user_text", ""))
    state["mode"] = p["mode"]
    state["plan"] = p
    return state

# --- Placeholder nodes for each mode. We will replace these later. ---

def answer_node(state: State) -> State:
    user_text = state.get("user_text", "")
    state["results"] = [{"message": f"Answer placeholder. You said: {user_text}"}]
    return state

def sql_summary_node(state: State) -> State:
    # Later: peek schema -> ask model for one SQL query -> validate -> preview.
    state["results"] = [{"message": "SQL Summary placeholder. Mode was 'write_sql'."}]
    return state

def covers_summary_node(state: State) -> State:
    # Later: query MP3s by time window -> ensure thumbnails -> compute pHash counts.
    state["results"] = [{"message": "Covers Summary placeholder. Mode was 'show_covers'."}]
    return state

def build_app():
    g = StateGraph(State)

    # Nodes
    g.add_node("Entry", entry)
    g.add_node("Planner", planner_node)
    g.add_node("Answer", answer_node)
    g.add_node("SqlSummary", sql_summary_node)
    g.add_node("CoversSummary", covers_summary_node)

    # Linear: Entry -> Planner
    g.set_entry_point("Entry")
    g.add_edge("Entry", "Planner")

    # Branch directly after Planner based on state["mode"]
    g.add_conditional_edges(
        "Planner",
        lambda state: route(state.get("mode", "answer")),
        {
            "Answer": "Answer",
            "SqlSummary": "SqlSummary",
            "CoversSummary": "CoversSummary",
        },
    )

    # End each branch
    g.add_edge("Answer", END)
    g.add_edge("SqlSummary", END)
    g.add_edge("CoversSummary", END)
    return g.compile()
