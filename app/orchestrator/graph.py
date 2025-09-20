"""Wire the graph: Entry -> Planner -> (branch) -> END."""
from langgraph.graph import StateGraph, END
from app.state import State
from app.orchestrator.planner import plan
from app.orchestrator.router import route

# Import subgraphs
from app.orchestrator.modes.ui import build_ui_app
from app.orchestrator.modes.data import build_data_app
from app.orchestrator.modes.agent import build_agent_app

def entry(state: State) -> State:
    return state

def planner_node(state: State) -> State:
    p = plan(state.get("user_text", ""))
    state["mode"] = p["mode"]
    state["plan"] = p
    return state

# --- Placeholder nodes we kept from earlier (you can remove later) ---

def answer_node(state: State) -> State:
    user_text = state.get("user_text", "")
    state["results"] = [{"message": f"Answer placeholder. You said: {user_text}"}]
    return state

def sql_summary_node(state: State) -> State:
    state["results"] = [{"message": "SQL Summary placeholder. Mode was 'write_sql'."}]
    return state

def covers_summary_node(state: State) -> State:
    state["results"] = [{"message": "Covers Summary placeholder. Mode was 'show_covers'."}]
    return state

def build_app():
    g = StateGraph(State)

    # Regular nodes
    g.add_node("Entry", entry)
    g.add_node("Planner", planner_node)
    g.add_node("Answer", answer_node)
    g.add_node("SqlSummary", sql_summary_node)
    g.add_node("CoversSummary", covers_summary_node)

    # Subgraph nodes (attach compiled subgraphs as nodes)
    g.add_node("UI", build_ui_app())
    g.add_node("Data", build_data_app())
    g.add_node("Agent", build_agent_app())

    # Entry then planner
    g.set_entry_point("Entry")
    g.add_edge("Entry", "Planner")

    # Conditional branch after planner
    g.add_conditional_edges(
        "Planner",
        lambda state: route(state.get("mode", "answer")),
        {
            "Answer": "Answer",
            "SqlSummary": "SqlSummary",
            "CoversSummary": "CoversSummary",
            "UI": "UI",
            "Data": "Data",
            "Agent": "Agent",
        },
    )

    # End each branch
    for name in ("Answer", "SqlSummary", "CoversSummary", "UI", "Data", "Agent"):
        g.add_edge(name, END)

    return g.compile()
