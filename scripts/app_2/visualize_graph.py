# app_2/visualize_graph.py
"""
Generate visual representations of the LangGraph workflow.

Run this script to generate:
1. A Mermaid diagram (text format, can be rendered at mermaid.live)
2. A PNG image (if graphviz/pygraphviz is installed)

Usage:
    python -m app_2.visualize_graph
"""
import os
from app_2.graph import build_app


def visualize():
    """Generate graph visualizations."""
    app = build_app()
    graph = app.get_graph()

    output_dir = os.path.dirname(__file__)

    # Generate Mermaid diagram (always works)
    print("Generating Mermaid diagram...")
    mermaid_text = graph.draw_mermaid()
    mermaid_path = os.path.join(output_dir, "../../app_2/graph_diagram.mmd")
    with open(mermaid_path, "w") as f:
        f.write(mermaid_text)
    print(f"Mermaid diagram saved to: {mermaid_path}")
    print("\nYou can visualize this at: https://mermaid.live")
    print("\n--- Mermaid Diagram ---")
    print(mermaid_text)
    print("--- End Diagram ---\n")

    # Try to generate PNG (requires graphviz)
    try:
        print("Attempting to generate PNG image...")
        png_data = graph.draw_mermaid_png()
        png_path = os.path.join(output_dir, "../../app_2/graph_diagram.png")
        with open(png_path, "wb") as f:
            f.write(png_data)
        print(f"PNG image saved to: {png_path}")
    except Exception as e:
        print(f"Could not generate PNG (this is optional): {e}")
        print("To enable PNG generation, install: pip install pygraphviz")

    print("\nVisualization complete!")


if __name__ == "__main__":
    visualize()
