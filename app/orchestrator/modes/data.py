from langgraph.graph import StateGraph, END
from app.state import State

def data_entry(state: State) -> State:
    args = (state.get("plan") or {}).get("args", {})
    print("[DATA] data_query with args:", args)
    state["results"] = [{"subgraph": "Data", "received": args}]
    return state

def build_data_app():
    g = StateGraph(State)
    g.add_node("DataEntry", data_entry)
    g.set_entry_point("DataEntry")
    g.add_edge("DataEntry", END)
    return g.compile()
