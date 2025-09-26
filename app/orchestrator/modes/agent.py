from langgraph.graph import StateGraph, END
from app.state import State

def agent_entry(state: State) -> State:
    args = (state.get("plan") or {}).get("args", {})
    print("[AGENT] agent mode with args:", args)
    state["results"] = [{"subgraph": "Agent", "received": args}]
    return state

def build_agent_app():
    g = StateGraph(State)
    g.add_node("AgentEntry", agent_entry)
    g.set_entry_point("AgentEntry")
    g.add_edge("AgentEntry", END)
    return g.compile()
