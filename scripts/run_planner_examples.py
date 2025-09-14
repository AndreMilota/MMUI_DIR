# scripts/run_planner_examples.py
from app.orchestrator.graph import build_app

def run(msg: str):
    app = build_app()
    out = app.invoke({"user_text": msg})
    print(f"\nINPUT: {msg}\nOUTPUT:", out.get("results"))

if __name__ == "__main__":
    run("Hello graph — just testing the placeholder answer.")
    run("Please show the album cover I downloaded last month.")
    run("Write SQL to summarize recent audio files.")
