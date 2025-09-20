"""Data subgraph: placeholder that announces itself and returns a result."""
from langgraph.graph import StateGraph, END
from app.state import State

def data_entry(state: State) -> State:
    print("[DATA] Data subgraph is running.")
    state["results"] = [{"subgraph": "Data", "message": "Data subgraph ran"}]
    return state

def build_data_app():
    g = StateGraph(State)
    g.add_node("DataEntry", data_entry)
    g.set_entry_point("DataEntry")
    g.add_edge("DataEntry", END)
    return g.compile()
