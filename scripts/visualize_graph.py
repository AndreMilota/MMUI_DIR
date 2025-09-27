# scripts/visualize_graph.py
# Purpose: print an ASCII graph in the console and save a Mermaid diagram to docs/graph.md

import sys
from pathlib import Path

# Make the project root importable when running this script directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.orchestrator.graph import build_app  # noqa: E402

def main():
    # Build the compiled graph
    app = build_app()
    g = app.get_graph()

    # 1) Print ASCII to console (no extra installs needed)
    print("\n=== ASCII graph ===")
    g.print_ascii()  # prints directly

    # 2) Save Mermaid to docs/graph.md so GitHub can render it
    mermaid = g.draw_mermaid()
    docs_dir = Path("docs")
    docs_dir.mkdir(parents=True, exist_ok=True)
    md_path = docs_dir / "graph.md"

    md = (
        "# MMUI_DIR — Current Graph\n\n"
        "The diagram below is generated automatically from LangGraph.\n\n"
        "```mermaid\n"
        f"{mermaid}\n"
        "```\n"
    )
    md_path.write_text(md, encoding="utf-8")
    print(f"\nSaved Mermaid diagram to: {md_path.resolve()}")

if __name__ == "__main__":
    main()
