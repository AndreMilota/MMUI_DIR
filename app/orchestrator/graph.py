"""Entry -> PlannerLLM -> (UI | Data | Agent) -> END"""
from langgraph.graph import StateGraph, END
from app.state import State
from app.orchestrator.router import route
from app.orchestrator.modes.ui import build_ui_app
from app.orchestrator.modes.data import build_data_app
from app.orchestrator.modes.agent import build_agent_app
from app.orchestrator.planner_llm import plan_with_llm
from app.memory import store as mem

def entry(state: State) -> State:
    return state

def planner_node(state: State) -> State:
    session_id = state.get("session_id", "default")
    memory = mem.load(session_id)
    plan = plan_with_llm(state.get("user_text", ""), state.get("pointers"), memory)
    state["mode"] = plan["mode"]
    state["plan"] = plan

    # Update memory with any resolved entities and pointers; remember last mode
    args = plan.get("args", {})
    updates = {
        "last_mode": plan["mode"],
        "last_entity": args.get("entity") or memory.get("last_entity"),
        "last_window": args.get("window") or memory.get("last_window"),
        "last_folder": args.get("from_folder") or memory.get("last_folder"),
        "last_disk": args.get("to_disk") or memory.get("last_disk"),
    }
    mem.merge(session_id, updates)
    return state

def build_app():
    g = StateGraph(State)
    g.add_node("Entry", entry)
    g.add_node("Planner", planner_node)

    # Attach subgraphs as nodes
    g.add_node("UI", build_ui_app())
    g.add_node("Data", build_data_app())
    g.add_node("Agent", build_agent_app())

    g.set_entry_point("Entry")
    g.add_edge("Entry", "Planner")

    g.add_conditional_edges(
        "Planner",
        lambda s: route(s.get("mode", "agent")),
        {"UI": "UI", "Data": "Data", "Agent": "Agent"},
    )

    for name in ("UI", "Data", "Agent"):
        g.add_edge(name, END)
    return g.compile()
