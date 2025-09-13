# hello_langgraph.py
from typing import TypedDict
import os
from langgraph.graph import StateGraph, END
from openai import OpenAI

# ----- Graph state shape -----
class State(TypedDict):
    user_text: str
    answer: str

# ----- A single node that calls Groq via the OpenAI client -----
def call_groq(state: State) -> State:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise SystemExit("GROQ_API_KEY is not set. Set it in your system or .env file.")

    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
    )

    response = client.responses.create(
        model="llama-3.3-70b-versatile",
        input=f"Reply in one short sentence to: {state['user_text']}"
    )

    text = getattr(response, "output_text", None)
    if not text:
        # Fallback: show the whole response so we can diagnose if needed
        print("Full response (no output_text field):")
        print(response)
        raise SystemExit("Model response did not include text content.")

    state["answer"] = text
    return state

# ----- Wire the graph -----
g = StateGraph(State)
g.add_node("CallGroq", call_groq)
g.set_entry_point("CallGroq")
g.add_edge("CallGroq", END)
app = g.compile()

if __name__ == "__main__":
    result = app.invoke({"user_text": "What is LangGraph?"})
    print(result["answer"])
