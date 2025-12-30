# scripts/run_graph_once.py
# Simple test script to run the database query graph with an example

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.runner import run_query

def run_example():
    """Run a single example query through the graph."""
    # Example: Count MP3 files more than a year old in a specific directory
    # For now, we'll use a general query - replace with actual path as needed
    example_query = "How many mp3 files do I have that are more than a week old?"

    print(f"\n{'='*60}")
    print(f"USER QUERY: {example_query}")
    print(f"{'='*60}\n")

    result = run_query(example_query)

    print(f"GENERATED SQL:\n{result['sql']}\n")
    print(f"{'='*60}")

    if result.get('error'):
        print(f"ERROR: {result['error']}\n")
    else:
        print(f"FOUND {len(result.get('results', []))} ROWS\n")
        print(f"RESPONSE:\n{result.get('response')}\n")

    print(f"{'='*60}\n")

if __name__ == "__main__":
    run_example()
