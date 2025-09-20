# scripts/run_route_demo.py
from app.runner import run_command

tests = [
    "ui: refresh gallery",
    "data: delete temp files older than 7 days",
    "agent: plan a cleanup",
    "Please show the album cover I downloaded last month.",
    "Write SQL to summarize recent audio files.",
]

if __name__ == "__main__":
    for t in tests:
        out = run_command(t)
        print("\nINPUT:", t)
        print("MODE:", out["mode"])
        print("RESULTS:", out["results"])
