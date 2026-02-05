# app/graph.py
"""LangGraph workflow for natural language database queries.

Flow: user_text → SQL → execute → results → natural language response
"""
import sqlite3
from pathlib import Path
from langgraph.graph import StateGraph, END
from app.state import State
from app.llm.core import chat
from file_scan.fs_database import LLM_DB_SCHEMA_DOC
import os

# python
def locate_db(filename="file_database.sqlite", folder="file_scan", max_levels=8):
    """Search upward from cwd and this file's directory for folder/filename."""
    starts = [Path.cwd(), Path(__file__).resolve().parent]
    for start in starts:
        p = start
        for _ in range(max_levels + 1):
            candidate = p / folder / filename
            if candidate.exists():
                return candidate.resolve()
            if p.parent == p:
                break
            p = p.parent
    # fallback to relative path (may be used when packaging)
    fallback = Path(folder) / filename
    return fallback.resolve() if fallback.exists() else fallback

DB_PATH = locate_db()
# removed `current_directory` - not needed

def text_to_sql(state: State) -> State:
    """Node 1: Convert natural language query to SQL using LLM."""
    user_text = state.get("user_text", "")

    system_prompt = f"""You are a SQL query generator for a file management database.

{LLM_DB_SCHEMA_DOC}

Your task:
1. Read the user's natural language query
2. Generate a valid SQLite query that answers their question
3. Return ONLY the SQL query, nothing else - no explanations, no markdown, no extra text

Important:
- Use proper JOINs between files, directories, and volumes tables
- Full file paths are: directories.dir_path || '/' || files.name || '.' || files.extension
- Filter for presence_state = 0 (PRESENT files) unless user asks for historical data
- For time-based queries, mtime_ns is in nanoseconds since Unix epoch
- Be careful with NULL values in optional fields
"""

    user_prompt = f"Generate SQL for this query: {user_text}"

    sql = chat(system_prompt, user_prompt, temperature=0.0)
    sql = sql.strip().strip('`').strip()  # Remove markdown code fences if present
    if sql.lower().startswith('sql\n'):
        sql = sql[4:].strip()

    state["sql"] = sql
    return state


def execute_sql(state: State) -> State:
    """Node 2: Execute the SQL query against the file_scan database."""
    sql = state.get("sql")

    if not sql:
        state["error"] = "No SQL query generated"
        state["results"] = []
        return state

    try:
        conn = sqlite3.connect(state.get("db_path") or DB_PATH)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()

        cursor.execute(sql)
        rows = cursor.fetchall()

        # Convert Row objects to dictionaries
        results = [dict(row) for row in rows]

        conn.close()

        state["results"] = results
        state["error"] = None

    except Exception as e:
        state["error"] = f"SQL execution error: {str(e)}"
        state["results"] = []

    return state


def sql_to_text(state: State) -> State:
    """Node 3: Convert SQL results to natural language response."""
    user_text = state.get("user_text", "")
    sql = state.get("sql", "")
    results = state.get("results", [])
    error = state.get("error")
    # read the time values
    now_ns = state.get("now_ns")
    now_iso = state.get("now_iso")

    if error:
        # If there was an error, return a helpful message
        system_prompt = "You are a helpful assistant. Explain this database error in simple terms."
        user_prompt = f"The user asked: '{user_text}'\n\nError: {error}\n\nExplain what went wrong."
        response = chat(system_prompt, user_prompt, temperature=0.3)
        state["response"] = response
        return state

    system_prompt = """You are a helpful file management assistant.

Your task:
1. Read the user's original question
2. Read the SQL query that was generated
3. Read the results from the database
4. Provide a clear, natural language answer to the user's question

Be concise and direct. If there are no results, say so clearly.
If there are many results, summarize them appropriately."""

    user_prompt = f"""User asked: "{user_text}"

SQL query used:
{sql}

Results ({len(results)} rows):
{results[:10] if len(results) > 10 else results}
{"..." if len(results) > 10 else ""}

Provide a natural language answer to the user's question."""

    response = chat(system_prompt, user_prompt, temperature=0.3)
    state["response"] = response

    return state


def build_app():
    """Build and compile the LangGraph workflow."""
    graph = StateGraph(State)

    # Add the three nodes
    graph.add_node("text_to_sql", text_to_sql)
    graph.add_node("execute_sql", execute_sql)
    graph.add_node("sql_to_text", sql_to_text)

    # Define the flow: text_to_sql → execute_sql → sql_to_text → END
    graph.set_entry_point("text_to_sql")
    graph.add_edge("text_to_sql", "execute_sql")
    graph.add_edge("execute_sql", "sql_to_text")
    graph.add_edge("sql_to_text", END)

    return graph.compile()
