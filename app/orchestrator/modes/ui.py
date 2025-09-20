"""UI subgraph: placeholder that announces itself and returns a result."""
from langgraph.graph import StateGraph, END
from app.state import State

def ui_entry(state: State) -> State:
    print("[UI] UI subgraph is running.")
    state["results"] = [{"subgraph": "UI", "message": "UI subgraph ran"}]
    return state

def build_ui_app():
    g = StateGraph(State)
    g.add_node("UIEntry", ui_entry)
    g.set_entry_point("UIEntry")
    g.add_edge("UIEntry", END)
    return g.compile()
