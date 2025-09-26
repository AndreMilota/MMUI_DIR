from langgraph.graph import StateGraph, END
from app.state import State

def ui_entry(state: State) -> State:
    args = (state.get("plan") or {}).get("args", {})
    print("[UI] ui_control with args:", args)
    state["results"] = [{"subgraph": "UI", "received": args}]
    return state

def build_ui_app():
    g = StateGraph(State)
    g.add_node("UIEntry", ui_entry)
    g.set_entry_point("UIEntry")
    g.add_edge("UIEntry", END)
    return g.compile()
