# scripts/app_2/branching_agent_tests.py
"""
Coordinator for all app_2 branch tests.

Each branch of the LangGraph workflow has its own test file:
  test_query_respond.py   - single value queries (count, sum, yes/no)
  test_query_display.py   - table display, sorting, grouping
  test_query_store.py     - multi-turn dialog storage
  test_query_transform.py - file move, rename, delete
  test_query_copy.py      - file copy operations
  test_query_feed_llm.py  - AI processing / SQL-incapable transforms
  test_query_external.py  - external app invocation (e.g. ffmpeg)
  test_web_search.py      - web research queries
  test_direct_answer.py   - conversational queries

Run this file to execute all branches in sequence.
Run an individual file to focus on one branch at a time.
"""
import sys
import os

# Add this directory to the path so the per-branch files can be imported
sys.path.insert(0, os.path.dirname(__file__))

from test_query_respond import test_all_respond
from test_query_display import test_all_display
from test_query_store import test_all_store
from test_query_transform import test_all_transform
from test_query_copy import test_all_copy
from test_query_feed_llm import test_all_feed_llm
from test_query_external import test_all_external
from test_web_search import test_all_web_search
from test_direct_answer import test_all_direct_answer


def test_all_branches():
    """Run all branch tests in sequence."""
    print("\n" + "#"*70)
    print("# RUNNING ALL BRANCHING AGENT TESTS")
    print("#"*70)

    # test_all_respond()     # uncomment to include
    test_all_display()
    test_all_store()
    test_all_transform()
    test_all_copy()
    test_all_feed_llm()
    test_all_external()
    test_all_web_search()
    test_all_direct_answer()

    print("\n" + "#"*70)
    print("# ALL TESTS COMPLETED")
    print("#"*70)


if __name__ == "__main__":
    test_all_branches()
