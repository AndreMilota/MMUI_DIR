"""Minimal graph wiring: Entry -> Answer -> END.

We will add the planner and router in the next step.
"""
from langgraph.graph import StateGraph, END
from app.state import State

def entry(state: State) -> State:
    # Expect state["user_text"] to be present
    return state

def answer_node(state: State) -> State:
    # Placeholder: just echo the user's text in a structured result
    user_text = state.get("user_text", "")
    state["results"] = [{"message": f"Answer placeholder. You said: {user_text}"}]
    return state

def build_app():
    g = StateGraph(State)
    g.add_node("Entry", entry)
    g.add_node("Answer", answer_node)

    g.set_entry_point("Entry")
    g.add_edge("Entry", "Answer")
    g.add_edge("Answer", END)
    return g.compile()
