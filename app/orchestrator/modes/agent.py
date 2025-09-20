"""Agent subgraph: placeholder that announces itself and returns a result."""
from langgraph.graph import StateGraph, END
from app.state import State

def agent_entry(state: State) -> State:
    print("[AGENT] Agent subgraph is running.")
    state["results"] = [{"subgraph": "Agent", "message": "Agent subgraph ran"}]
    return state

def build_agent_app():
    g = StateGraph(State)
    g.add_node("AgentEntry", agent_entry)
    g.set_entry_point("AgentEntry")
    g.add_edge("AgentEntry", END)
    return g.compile()
