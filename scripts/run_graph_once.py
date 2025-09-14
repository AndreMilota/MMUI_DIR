# scripts/run_graph_once.py
from app.orchestrator.graph import build_app

if __name__ == "__main__":
    app = build_app()
    out = app.invoke({"user_text": "Hello graph — just testing the placeholder answer."})
    print(out.get("results"))
