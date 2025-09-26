# scripts/run_llm_routing_demo.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.runner import run_command

def show(out):
    print("MODE:", out["mode"])
    print("PLAN:", out["plan"])
    print("RESULTS:", out["results"])

if __name__ == "__main__":
    sid = "demo-session-1"

    print("\n--- UI control: close a specific window ---")
    out = run_command(sid, "close this window", pointers={"window": "a21b"})
    show(out)

    # print("\n--- Data query: mp3s from last month, folder -> disk ---")
    # out = run_command(
    #     sid,
    #     "show me all the mp3s I downloaded last month in this folder and then moved to this disk",
    #     pointers={"folder": "C:/downloads", "disk": "324fs2"},
    # )
    # show(out)
    #
    # print("\n--- Two-turn context: resolve entity, then search data ---")
    # # Turn 1: general agent interprets the band
    # out = run_command(sid, "What was that band in the 60s that had the hit 'All You Need Is Love'?")
    # show(out)
    # # Pretend the agent resolved 'The Beatles' and wrote it into memory (the LLM planner can also infer it)
    # # Turn 2: rely on 'them' -> routes to data_query carrying the entity forward via memory
    # out = run_command(sid, "Find me all the songs by them I have on my hard disks.")
    # show(out)
