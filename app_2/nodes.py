# app_2/nodes.py
"""
Processing nodes for the branching LangGraph workflow.

Nodes:
- classify_and_plan: Classifies user intent and generates execution plan
- execute_sql: Runs SQL against the database
- query_and_respond: Synthesizes query result to natural language
- query_and_display: Displays query result as a table
- query_and_store: Stores query result for multi-turn dialog
- query_and_transform: Processes source/dest for file operations (move/rename/delete)
- query_and_copy: Processes source/dest for copy operations
- query_feed_llm: Feeds query results to LLM for AI processing
- query_external: Calls external application per row
- web_search_handler: Performs web research
- direct_answer_handler: Returns direct response without querying
- format_response: Final node that prepares the response
"""
import sqlite3
import json
from typing import Dict, Any

from app_2.state import GraphState, ExecutionPlan, ActionType
from app.llm.core import chat, chat_json, extract_json_block
from app.utils.clipboard import print_copy
from file_scan.fs_database import LLM_DB_SCHEMA_DOC
from file_scan.mock_file_system.mock_files import MockFiles


# -----------------------------------------------------------------------------
# SQL Escalation Guidance - Modular Prompt Component
# -----------------------------------------------------------------------------
#
# MODULARIZATION MECHANISM EXPLANATION:
#
# This variable contains specialized guidance for the classifier LLM to help it
# decide when a file transformation request can be handled entirely within SQL
# versus when it needs to escalate to the query_feed_llm path.
#
# WHY MODULARIZE THIS?
# ---------------------
# 1. CONDITIONAL INCLUSION: In a production system, you may want to include this
#    guidance only when the user's request appears to involve file transformation.
#    A lightweight pre-classifier or keyword detector could determine whether to
#    inject this context, saving tokens on simple queries.
#
# 2. A/B TESTING: By isolating this guidance, you can easily test different
#    versions of the escalation rules to optimize classification accuracy.
#
# 3. MODEL-SPECIFIC TUNING: Different LLMs may need different levels of detail
#    in the guidance. Smaller models might need more explicit examples, while
#    larger models might work with more concise rules.
#
# 4. DYNAMIC UPDATES: The guidance can be loaded from a config file or database,
#    allowing updates without code changes.
#
# FUTURE OPTIMIZATION POSSIBILITIES:
# ----------------------------------
# - Use a lightweight classifier (e.g., regex patterns, keyword matching, or a
#   small fine-tuned model) to detect transformation-related queries before
#   injecting this guidance.
#
# - Implement a two-stage classification: First classify intent broadly, then
#   only inject SQL capability guidance for transform/copy/rename intents.
#
# - Cache the compiled prompt with guidance for requests that pattern-match
#   known transformation scenarios.
#
# - Use embedding similarity to compare the user's request against known
#   SQL-capable vs SQL-incapable transformation patterns.
#
# HOW TO USE CONDITIONALLY:
# -------------------------
# Currently, this guidance is always included in the system prompt. To make it
# conditional, you would:
#
#   1. Create a pre-classification function:
#      def needs_sql_escalation_guidance(user_input: str) -> bool:
#          transform_keywords = ['rename', 'move', 'delete', 'copy', 'change name']
#          return any(kw in user_input.lower() for kw in transform_keywords)
#
#   2. Conditionally include in the prompt:
#      escalation_section = SQL_ESCALATION_GUIDANCE if needs_sql_escalation_guidance(user_input) else ""
#      system_prompt = f"...{escalation_section}..."
#
# -----------------------------------------------------------------------------

SQL_ESCALATION_GUIDANCE = """
## SQL String Manipulation Capabilities and Limitations

When generating SQL for file transformation operations (query_transform, query_copy),
you must understand what SQLite CAN and CANNOT do with string manipulation.

### SQLite CAN handle (use query_transform or query_copy):

1. **Moving files to a new directory**: Simply change the directory portion
   Example: Move all .pdf from /Downloads to /Archive
   SQL: SELECT source_path, '/Archive/' || name || '.' || extension AS dest_path ...

2. **Deleting files**: dest_path is NULL
   Example: Delete all .tmp files
   SQL: SELECT source_path, NULL AS dest_path ...

3. **Removing a FIXED, KNOWN prefix or suffix**: Use REPLACE()
   Example: Remove 'archive_' prefix from all filenames
   SQL: SELECT source_path, dir_path || '/' || REPLACE(name, 'archive_', '') || '.' || extension AS dest_path ...

4. **Removing first N characters** (fixed count): Use SUBSTR()
   Example: Remove first 4 characters from all filenames
   SQL: SUBSTR(name, 5) -- starts at position 5, skipping first 4

5. **Extracting after a fixed delimiter**: Use SUBSTR() with INSTR()
   Example: Get everything after the first underscore
   SQL: SUBSTR(name, INSTR(name, '_') + 1)

### SQLite CANNOT handle (MUST use query_feed_llm):

1. **Variable-length pattern removal**: Removing "leading digits" of any length
   Example: "01_song.mp3", "123_track.mp3" -> "song.mp3", "track.mp3"
   WHY: No regex support. Can't match "any number of digits followed by underscore"

2. **CamelCase to snake_case conversion**:
   Example: "UserAccountManager.py" -> "user_account_manager.py"
   WHY: Requires identifying uppercase letters mid-string and inserting underscores

3. **Removing variable-content parenthetical suffixes**:
   Example: "file (1).txt", "file (copy).txt" -> "file.txt"
   WHY: Content inside parentheses varies; can't use fixed REPLACE()

4. **Pattern-based extraction and restructuring**:
   Example: "IMG_0001.jpg" -> "vacation_0001.jpg" (keeping the number)
   WHY: Requires regex capture groups to extract the number portion

5. **Semantic/AI-based renaming**:
   Example: Rename photos based on their metadata or content
   WHY: Requires understanding context, not just string manipulation

6. **Complex conditional renaming**:
   Example: "If starts with X, do A; if starts with Y, do B; otherwise do C"
   WHY: While CASE statements exist, complex multi-condition string transforms
   become unwieldy and error-prone in SQL

### Decision Rule:

- If the transformation can be expressed with REPLACE(), SUBSTR(), ||, or simple
  CASE statements with fixed string comparisons: Use query_transform or query_copy

- If the transformation requires pattern matching, variable-length matching,
  regex-like operations, or semantic understanding: Use query_feed_llm and write
  SQL that returns source_path plus any columns needed for the LLM to decide new names.

### SQL Template for query_feed_llm:

IMPORTANT: Always JOIN the files and directories tables properly. Never reference
dir_path directly on the files table - it lives in directories.

```sql
SELECT
    directories.dir_path || '/' || files.name ||
        CASE WHEN files.extension IS NOT NULL AND files.extension != ''
             THEN '.' || files.extension ELSE '' END AS source_path,
    directories.dir_path,
    files.name,
    files.extension
FROM files
JOIN directories ON files.directory_id = directories.id
WHERE directories.dir_path = 'C:/Some/Path'
  AND files.presence_state = 0
```

The LLM processing node will then use these columns to generate dest_path values.
"""


# -----------------------------------------------------------------------------
# Default Scope Guidance - Modular Prompt Component
# -----------------------------------------------------------------------------
#
# MODULARIZATION MECHANISM EXPLANATION:
#
# This variable controls how the classifier generates SQL when the user
# specifies (or doesn't specify) a directory. It enforces the principle of
# least surprise: if you ask about "C:/Documents", you mean that folder,
# not every file buried in subdirectories.
#
# WHY MODULARIZE THIS?
# ---------------------
# This guidance is broadly applicable — it should be injected into the
# classifier whenever the action type involves a database query (query_display,
# query_respond, query_store, query_transform, query_copy, query_feed_llm).
# Keeping it in one variable means it can be updated once and the change
# propagates to every prompt that includes it.
#
# FUTURE OPTIMIZATION POSSIBILITIES:
# ----------------------------------
# - Keyword spotting: detect "recursively", "all subfolders", "anywhere in"
#   etc. and conditionally override the default (could also let the model do
#   this, but a deterministic pre-check saves tokens and is more reliable).
#
# - User preference layer: allow a per-session preference ("always recurse by
#   default") stored in GraphState that overrides this guidance.
#
# HOW TO USE CONDITIONALLY:
# -------------------------
# Currently always included. To make conditional:
#
#   scope_section = DEFAULT_SCOPE_GUIDANCE if action_involves_db else ""
#
# -----------------------------------------------------------------------------

DEFAULT_SCOPE_GUIDANCE = """
## Default Query Scope: Current Directory Level Only

When the user specifies a particular directory path, query ONLY the files
directly at that level — do NOT include files in subdirectories.

Use an exact match:
  WHERE directories.dir_path = 'C:/Some/Path'

NOT a LIKE pattern:
  WHERE directories.dir_path LIKE 'C:/Some/Path/%'  ← wrong unless recursive requested

Recurse into subdirectories ONLY when the user explicitly indicates it:
- "including subfolders / subdirectories"
- "recursively" / "and all subfolders"
- No specific directory is given at all (e.g. "find all my MP3s" — must scan everywhere)
- The user names a root or drive with no subdirectory (e.g. "everything on C:")

Examples:
- "Show files in C:/Documents" → exact match only (C:/Documents)
- "Show files in C:/Documents and its subfolders" → LIKE pattern
- "Find all .log files" → recursive (no directory specified)
"""


# -----------------------------------------------------------------------------
# Query Display Guidance - Modular Prompt Component
# -----------------------------------------------------------------------------
#
# MODULARIZATION MECHANISM EXPLANATION:
#
# This variable contains formatting rules that apply specifically to the
# query_display branch. They govern which columns to SELECT and how to
# present timestamps and paths so the rendered table is immediately readable.
#
# WHY MODULARIZE THIS?
# ---------------------
# 1. CONDITIONAL INCLUSION: This guidance only needs to be injected when the
#    classifier has determined (or is likely to determine) that the action is
#    query_display. A pre-classifier or keyword spotter could detect display
#    intent ("show me", "list", "what files") and include this guidance only
#    then, reducing prompt size for other branches.
#
# 2. A/B TESTING: Column layout and time formatting are stylistic choices.
#    Keeping them in one place makes it easy to experiment with alternatives
#    (e.g. ISO-8601 vs "Jan 10 2026", separate path/name vs combined).
#
# 3. MODEL-SPECIFIC TUNING: Smaller models may need more explicit examples;
#    larger models may need only the rules. This variable can be swapped per
#    model without touching the rest of the prompt.
#
# FUTURE OPTIMIZATION POSSIBILITIES:
# ----------------------------------
# - RAG retrieval: store multiple display style snippets in a vector store and
#   retrieve the most relevant one based on the query (e.g. "music files" →
#   retrieve guidance that also includes duration/bitrate columns).
#
# - Keyword spotting: detect "full path", "with path", "just names" etc. to
#   override the defaults before sending to the model.
#
# - User preference layer: persist display preferences in GraphState
#   (e.g. prefer ISO timestamps, always show full path) and inject overrides
#   here at runtime.
#
# HOW TO USE CONDITIONALLY:
# -------------------------
# Currently always included. To make conditional:
#
#   def looks_like_display_query(user_input: str) -> bool:
#       keywords = ['show', 'list', 'display', 'what files', 'which files']
#       return any(kw in user_input.lower() for kw in keywords)
#
#   display_section = QUERY_DISPLAY_GUIDANCE if looks_like_display_query(user_input) else ""
#
# -----------------------------------------------------------------------------

QUERY_DISPLAY_GUIDANCE = """
## Display Formatting Rules (query_display)

### 1. Timestamps — Human-Readable by Default
When selecting time columns (mtime_ns, ctime_ns), convert them to a readable
string unless the user asks for raw or numeric values:
  datetime(mtime_ns / 1000000000, 'unixepoch') AS modified
  datetime(ctime_ns / 1000000000, 'unixepoch') AS created

### 2. Path Column — Based on SQL Structure, Not Query Wording

The rule is simple: look at the WHERE clause you are about to write.

- If the WHERE clause pins results to ONE exact directory using
  `directories.dir_path = 'C:/Some/Path'` (exact equality, not LIKE),
  then ALL results come from that same location. The path is already
  known to the user — do NOT include a path column. Select filename only:
    files.name || CASE WHEN files.extension != '' THEN '.' || files.extension ELSE '' END AS filename

  This applies even when filtering by other attributes (artist, size,
  date, type, etc.) — if the directory is pinned, filename only is correct.
  Example: "list Beatles files in C:/Music/Beatles" → exact dir filter →
  filename column only, even though the filter is on tag_artist.

- If the WHERE clause uses LIKE for a directory prefix, has no directory
  filter, or could match files across multiple directories, include the
  directory path in its own dedicated column:
    directories.dir_path AS path,
    files.name || CASE WHEN files.extension != '' THEN '.' || files.extension ELSE '' END AS filename

  Do NOT concatenate path and filename into one long string — keep them
  as separate columns so the table is easy to scan.
"""


# -----------------------------------------------------------------------------
# Classification Node
# -----------------------------------------------------------------------------

def classify_and_plan(state: GraphState) -> GraphState:
    """
    Node 1: Classify user intent and generate an execution plan.

    This node makes a single LLM call that:
    1. Determines which action type (branch) to use
    2. Generates SQL if needed
    3. Provides processing instructions
    """
    user_input = state.get("user_input", "")
    now_ns = state.get("now_ns")
    now_iso = state.get("now_iso")

    system_prompt = f"""You are an intent classifier and SQL generator for a file management system.

Current time (ISO): {now_iso}
Current time (nanoseconds since epoch): {now_ns}

{LLM_DB_SCHEMA_DOC}

Your task is to:
1. Classify the user's intent into one of these action types:
   - query_respond: User wants a single value answer (count, sum, yes/no) synthesized to natural language
   - query_display: User wants to see a table of files displayed
   - query_store: User describes files for later reference in conversation (store but don't display)
   - query_transform: User wants to move, rename, or delete files (generate source/dest columns)
   - query_copy: User wants to copy files (generate source/dest columns)
   - query_feed_llm: User wants AI to process/analyze file data (e.g., AI-based renaming)
   - query_external: User wants to run an external program on files
   - web_search: User asks something requiring web lookup (not about their files)
   - direct_answer: User is chatting, greeting, or asking something you can answer directly

2. Generate SQL if the action requires database access
3. Provide clear processing instructions

For file operations (query_transform, query_copy):
- SQL must return columns: source_path (full path of file) and dest_path (destination or NULL for delete)
- Full path = directories.dir_path || '/' || files.name || '.' || files.extension

For query_feed_llm (when SQL cannot generate dest_path):
- SQL should return source_path and any other columns the LLM needs to make renaming decisions
- The LLM will then generate the dest_path values based on the retrieved data

{SQL_ESCALATION_GUIDANCE}

{DEFAULT_SCOPE_GUIDANCE}

{QUERY_DISPLAY_GUIDANCE}

For query_respond: SQL should return a single value (COUNT, SUM, etc.)

IMPORTANT SQL RULES:
- Filter for presence_state = 0 (PRESENT files) unless user asks for historical data
- NEVER use strftime('%s','now') or date('now') - use the literal now_ns value for time arithmetic
- ctime_ns is creation time; mtime_ns is modification time
- For relative time: compare directly against nanosecond values
  Example: "older than 7 days" means ctime_ns < {now_ns} - 7*86400*1000000000

Respond with a JSON object matching this schema:
{{
    "action_type": "query_respond|query_display|query_store|query_transform|query_copy|query_feed_llm|query_external|web_search|direct_answer",
    "sql": "SQL query or null",
    "processing_instruction": "what to do with results",
    "response_text": "direct response text if action_type is direct_answer, else null",
    "llm_instruction": "instructions for LLM if action_type is query_feed_llm, else null",
    "external_app": "app name if action_type is query_external, else null",
    "reasoning": "brief explanation of classification"
}}
"""

    user_prompt = f"Classify this request and generate an execution plan: {user_input}"

    response = chat_json(system_prompt, user_prompt, temperature=0.0)  # <------- LLM CALL: classify intent

    # Parse the JSON response
    json_str = extract_json_block(response)
    try:
        plan_dict = json.loads(json_str)
        plan = ExecutionPlan(**plan_dict)
    except Exception as e:
        # Fallback: treat as direct answer with error
        plan = ExecutionPlan(
            action_type=ActionType.DIRECT_ANSWER,
            processing_instruction="respond_directly",
            response_text=f"I had trouble understanding that request. Error: {str(e)}",
            reasoning="Failed to parse classification response"
        )

    state["execution_plan"] = plan
    state["sql"] = plan.sql
    return state


# -----------------------------------------------------------------------------
# SQL Execution Node (shared by query branches)
# -----------------------------------------------------------------------------

def execute_sql(state: GraphState) -> GraphState:
    """Execute the SQL query against the file database."""
    from app.graph import DB_PATH  # Use same DB discovery logic

    sql = state.get("sql")

    if not sql:
        state["query_error"] = "No SQL query to execute"
        state["query_result"] = []
        return state

    try:
        db_path = state.get("db_path") or DB_PATH
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql)  # <------- DATABASE QUERY
        rows = cursor.fetchall()
        conn.close()

        state["query_result"] = [dict(row) for row in rows]
        state["query_error"] = None

    except Exception as e:
        state["query_error"] = f"SQL execution error: {str(e)}"
        state["query_result"] = []

    return state


# -----------------------------------------------------------------------------
# Query Response Node (synthesize to natural language)
# -----------------------------------------------------------------------------

def query_and_respond(state: GraphState) -> GraphState:
    """Synthesize query result to natural language response."""
    user_input = state.get("user_input", "")
    sql = state.get("sql", "")
    results = state.get("query_result", [])
    error = state.get("query_error")
    plan = state.get("execution_plan")

    if error:
        system_prompt = "You are a helpful assistant. Explain this database error in simple terms."
        user_prompt = f"The user asked: '{user_input}'\n\nError: {error}\n\nExplain what went wrong."
        response = chat(system_prompt, user_prompt, temperature=0.3)  # <------- LLM CALL: explain error
        state["final_response"] = response
        return state

    system_prompt = """You are a helpful file management assistant.

Your task:
1. Read the user's original question
2. Read the SQL query results
3. Provide a clear, natural language answer

Be concise and direct. If there are no results, say so clearly."""

    user_prompt = f"""User asked: "{user_input}"

SQL query used:
{sql}

Results ({len(results)} rows):
{results[:10] if len(results) > 10 else results}
{"..." if len(results) > 10 else ""}

Provide a natural language answer to the user's question."""

    response = chat(system_prompt, user_prompt, temperature=0.3)  # <------- LLM CALL: synthesize response
    state["final_response"] = response
    return state


# -----------------------------------------------------------------------------
# Query Display Node (show table)
# -----------------------------------------------------------------------------

def query_and_display(state: GraphState) -> GraphState:
    """Display query results as a formatted table."""
    results = state.get("query_result", [])
    error = state.get("query_error")
    user_input = state.get("user_input", "")

    print(f"\n[NODE: query_and_display]")
    print(f"User request: {user_input}")

    if error:
        state["final_response"] = f"Error executing query: {error}"
        return state

    if not results:
        state["final_response"] = "No files found matching your criteria."
        return state

    # Print table header
    columns = list(results[0].keys())
    header = " | ".join(f"{col:<20}" for col in columns)
    separator = "-" * len(header)

    print(separator)
    print(header)
    print(separator)

    for row in results:
        row_str = " | ".join(f"{str(row.get(col, '')):<20}" for col in columns)
        print(row_str)

    print(separator)
    print(f"Total: {len(results)} rows")

    state["final_response"] = f"Displayed {len(results)} files matching your request."
    return state


# -----------------------------------------------------------------------------
# Query Store Node (store for multi-turn)
# -----------------------------------------------------------------------------

def query_and_store(state: GraphState) -> GraphState:
    """Store query results for later reference in conversation."""
    results = state.get("query_result", [])
    error = state.get("query_error")
    user_input = state.get("user_input", "")
    plan = state.get("execution_plan")

    print(f"\n[NODE: query_and_store]")
    print(f"User request: {user_input}")

    if error:
        state["final_response"] = f"Error executing query: {error}"
        return state

    # Store the table in state for later turns
    state["stored_table"] = results
    state["stored_table_description"] = user_input

    # Build table string for display and clipboard
    if results:
        columns = list(results[0].keys())
        header = " | ".join(f"{col:<20}" for col in columns)
        separator = "-" * len(header)

        # Build the full table as a string for clipboard
        table_lines = [separator, header, separator]
        for row in results:
            row_str = " | ".join(f"{str(row.get(col, '')):<20}" for col in columns)
            table_lines.append(row_str)
        table_lines.append(separator)
        table_lines.append(f"Stored {len(results)} rows for later reference")

        # Print table (regular print for trace info)
        for line in table_lines:
            print(line)

        # Copy summary to clipboard for accessibility
        summary = f"Stored {len(results)} files: " + ", ".join(
            str(row.get('name', row.get(columns[0], ''))) for row in results[:5]
        )
        if len(results) > 5:
            summary += f" ... and {len(results) - 5} more"
        print_copy(summary)

    state["final_response"] = f"Got it. I've noted {len(results)} files matching '{user_input}'. You can refer to them in follow-up requests."
    return state


# -----------------------------------------------------------------------------
# Query Transform Node (move/rename/delete)
# -----------------------------------------------------------------------------

def query_and_transform(state: GraphState) -> GraphState:
    """
    Process file transformation operations (move/rename/delete).

    Expects SQL to return source_path and dest_path columns.
    If dest_path is NULL, the file will be deleted.

    Uses file_system (MockFiles or real adapter) for operations when available.
    TODO: Integrate PathGuard before enabling real filesystem operations.
    """
    results = state.get("query_result", [])
    error = state.get("query_error")
    user_input = state.get("user_input", "")
    plan = state.get("execution_plan")
    file_system = state.get("file_system")
    use_real_fs = state.get("use_real_fs", False)

    print(f"\n[NODE: query_and_transform]")
    print(f"User request: {user_input}")
    print(f"Processing instruction: {plan.processing_instruction if plan else 'N/A'}")

    if error:
        state["final_response"] = f"Error executing query: {error}"
        return state

    if not results:
        state["final_response"] = "No files found matching your criteria for transformation."
        return state

    # SAFETY CHECK: If file_system is not a MockFiles instance it is a real filesystem.
    # Real filesystem operations require use_real_fs=True AND PathGuard (not yet integrated).
    # TODO: Add PathGuard validation here before production use
    is_real_fs = file_system is not None and not isinstance(file_system, MockFiles)
    if is_real_fs and not use_real_fs:
        print("ERROR: Real filesystem detected but use_real_fs=False. Requires PathGuard.")
        state["final_response"] = "Real filesystem operations are disabled for safety."
        state["operation_errors"] = ["Real filesystem requires use_real_fs=True and PathGuard integration"]
        return state

    # Print planned operations
    print("\nPlanned file operations:")
    print("-" * 80)
    print(f"{'Source Path':<40} | {'Destination':<35} | {'Status':<10}")
    print("-" * 80)

    delete_count = 0
    move_count = 0
    success_count = 0
    operation_results = []
    operation_errors = []

    for row in results:
        source = row.get("source_path", "???")
        dest = row.get("dest_path")
        status = "PENDING"
        op_result = {"source": source, "dest": dest, "success": False, "error": None}

        if dest is None:
            # DELETE operation
            delete_count += 1
            if file_system:
                try:
                    result = file_system.delete(source)  # <------- FILE OPERATION: delete
                    if result:
                        status = "DELETED"
                        op_result["success"] = True
                        success_count += 1
                    else:
                        status = "NOT FOUND"
                        op_result["error"] = "File not found"
                        operation_errors.append(f"Delete failed - file not found: {source}")
                except Exception as e:
                    status = "ERROR"
                    op_result["error"] = str(e)
                    operation_errors.append(f"Delete error for {source}: {e}")
            else:
                status = "SKIPPED"
                op_result["error"] = "No VFS available"
            dest_display = "[DELETE]"
        else:
            # MOVE/RENAME operation
            move_count += 1
            if file_system:
                try:
                    # Check if destination directory exists
                    dest_dir = "/".join(dest.replace("\\", "/").split("/")[:-1])
                    if not file_system.exists(dest_dir):
                        status = "DIR MISSING"
                        op_result["error"] = f"Destination directory does not exist: {dest_dir}"
                        operation_errors.append(f"Move failed - directory missing: {dest_dir}")
                    else:
                        file_id = file_system.move(source, dest)  # <------- FILE OPERATION: move
                        if file_id:
                            status = "MOVED"
                            op_result["success"] = True
                            success_count += 1
                        else:
                            status = "FAILED"
                            op_result["error"] = "Move returned None"
                            operation_errors.append(f"Move failed for {source}")
                except Exception as e:
                    status = "ERROR"
                    op_result["error"] = str(e)
                    operation_errors.append(f"Move error for {source}: {e}")
            else:
                status = "SKIPPED"
                op_result["error"] = "No VFS available"
            dest_display = dest

        operation_results.append(op_result)
        print(f"{source:<40} | {dest_display:<35} | {status:<10}")

    print("-" * 80)
    print(f"Total: {len(results)} files ({delete_count} deletes, {move_count} moves/renames)")
    if file_system:
        print(f"Completed: {success_count} successful, {len(operation_errors)} errors")
    else:
        print("[NO VFS: Operations not executed]")

    state["operation_results"] = operation_results
    state["operation_errors"] = operation_errors if operation_errors else None

    if file_system:
        state["final_response"] = f"Processed {len(results)} files: {success_count} successful, {len(operation_errors)} errors."
    else:
        state["final_response"] = f"Would process {len(results)} files: {delete_count} deletions, {move_count} moves/renames. (No VFS - operations skipped)"

    return state


# -----------------------------------------------------------------------------
# Query Copy Node
# -----------------------------------------------------------------------------

def query_and_copy(state: GraphState) -> GraphState:
    """
    Process file copy operations.

    Expects SQL to return source_path and dest_path columns.

    Uses file_system (MockFiles or real adapter) for operations when available.
    TODO: Integrate PathGuard before enabling real filesystem operations.
    """
    results = state.get("query_result", [])
    error = state.get("query_error")
    user_input = state.get("user_input", "")
    plan = state.get("execution_plan")
    file_system = state.get("file_system")
    use_real_fs = state.get("use_real_fs", False)

    print(f"\n[NODE: query_and_copy]")
    print(f"User request: {user_input}")
    print(f"Processing instruction: {plan.processing_instruction if plan else 'N/A'}")

    if error:
        state["final_response"] = f"Error executing query: {error}"
        return state

    if not results:
        state["final_response"] = "No files found matching your criteria for copying."
        return state

    # SAFETY CHECK: If file_system is not a MockFiles instance it is a real filesystem.
    # Real filesystem operations require use_real_fs=True AND PathGuard (not yet integrated).
    # TODO: Add PathGuard validation here before production use
    is_real_fs = file_system is not None and not isinstance(file_system, MockFiles)
    if is_real_fs and not use_real_fs:
        print("ERROR: Real filesystem detected but use_real_fs=False. Requires PathGuard.")
        state["final_response"] = "Real filesystem operations are disabled for safety."
        state["operation_errors"] = ["Real filesystem requires use_real_fs=True and PathGuard integration"]
        return state

    # Print planned operations
    print("\nPlanned copy operations:")
    print("-" * 80)
    print(f"{'Source Path':<40} | {'Destination':<35} | {'Status':<10}")
    print("-" * 80)

    success_count = 0
    operation_results = []
    operation_errors = []

    for row in results:
        source = row.get("source_path", "???")
        dest = row.get("dest_path", "???")
        status = "PENDING"
        op_result = {"source": source, "dest": dest, "success": False, "error": None}

        if file_system:
            try:
                # Check if destination directory exists
                dest_dir = "/".join(dest.replace("\\", "/").split("/")[:-1])
                if not file_system.exists(dest_dir):
                    status = "DIR MISSING"
                    op_result["error"] = f"Destination directory does not exist: {dest_dir}"
                    operation_errors.append(f"Copy failed - directory missing: {dest_dir}")
                elif not file_system.exists(source):
                    status = "NOT FOUND"
                    op_result["error"] = f"Source file does not exist: {source}"
                    operation_errors.append(f"Copy failed - source not found: {source}")
                else:
                    file_id = file_system.copy(source, dest)  # <------- FILE OPERATION: copy
                    if file_id:
                        status = "COPIED"
                        op_result["success"] = True
                        success_count += 1
                    else:
                        status = "FAILED"
                        op_result["error"] = "Copy returned None"
                        operation_errors.append(f"Copy failed for {source}")
            except Exception as e:
                status = "ERROR"
                op_result["error"] = str(e)
                operation_errors.append(f"Copy error for {source}: {e}")
        else:
            status = "SKIPPED"
            op_result["error"] = "No VFS available"

        operation_results.append(op_result)
        print(f"{source:<40} | {dest:<35} | {status:<10}")

    print("-" * 80)
    print(f"Total: {len(results)} files to copy")
    if file_system:
        print(f"Completed: {success_count} successful, {len(operation_errors)} errors")
    else:
        print("[NO VFS: Operations not executed]")

    state["operation_results"] = operation_results
    state["operation_errors"] = operation_errors if operation_errors else None

    if file_system:
        state["final_response"] = f"Copied {success_count} of {len(results)} files. {len(operation_errors)} errors."
    else:
        state["final_response"] = f"Would copy {len(results)} files. (No VFS - operations skipped)"

    return state


# -----------------------------------------------------------------------------
# Query Feed LLM Node
# -----------------------------------------------------------------------------

def query_feed_llm(state: GraphState) -> GraphState:
    """
    Feed query results to LLM for AI processing.

    Could be used for AI-based renaming, categorization, etc.
    """
    results = state.get("query_result", [])
    error = state.get("query_error")
    user_input = state.get("user_input", "")
    plan = state.get("execution_plan")

    print(f"\n[NODE: query_feed_llm]")
    print(f"User request: {user_input}")
    print(f"LLM instruction: {plan.llm_instruction if plan else 'N/A'}")

    if error:
        state["final_response"] = f"Error executing query: {error}"
        return state

    if not results:
        state["final_response"] = "No files found to process with AI."
        return state

    # Print what would be fed to the LLM
    print("\nFiles to be processed by LLM:")
    print("-" * 60)

    for i, row in enumerate(results[:10]):  # Show first 10
        print(f"{i+1}. {row}")

    if len(results) > 10:
        print(f"... and {len(results) - 10} more rows")

    print("-" * 60)
    print(f"\n[STUB: Would process {len(results)} rows through LLM with instruction: '{plan.llm_instruction if plan else 'N/A'}']")

    state["final_response"] = f"Would process {len(results)} files with AI. (Stub - no actual LLM processing performed)"
    return state


# -----------------------------------------------------------------------------
# Query External App Node
# -----------------------------------------------------------------------------

def query_external(state: GraphState) -> GraphState:
    """
    Call external application for each row of query results.
    """
    results = state.get("query_result", [])
    error = state.get("query_error")
    user_input = state.get("user_input", "")
    plan = state.get("execution_plan")

    print(f"\n[NODE: query_external]")
    print(f"User request: {user_input}")
    print(f"External app: {plan.external_app if plan else 'N/A'}")

    if error:
        state["final_response"] = f"Error executing query: {error}"
        return state

    if not results:
        state["final_response"] = "No files found to process with external application."
        return state

    # Print what would be sent to external app
    print(f"\nFiles to be processed by external app '{plan.external_app if plan else 'unknown'}':")
    print("-" * 60)

    for i, row in enumerate(results[:10]):
        print(f"{i+1}. {row}")

    if len(results) > 10:
        print(f"... and {len(results) - 10} more rows")

    print("-" * 60)
    print(f"\n[STUB: Would invoke '{plan.external_app if plan else 'app'}' for {len(results)} files]")

    state["final_response"] = f"Would process {len(results)} files with external app '{plan.external_app if plan else 'unknown'}'. (Stub - no actual invocation)"
    return state


# -----------------------------------------------------------------------------
# Web Search Node
# -----------------------------------------------------------------------------

def web_search_handler(state: GraphState) -> GraphState:
    """
    Handle requests that require web search/research.
    """
    user_input = state.get("user_input", "")
    plan = state.get("execution_plan")

    print(f"\n[NODE: web_search_handler]")
    print(f"User request: {user_input}")
    print(f"Processing instruction: {plan.processing_instruction if plan else 'N/A'}")
    print(f"\n[STUB: Would perform web search for: '{user_input}']")

    state["final_response"] = f"I would search the web for information about: '{user_input}'. (Stub - no actual web search performed)"
    return state


# -----------------------------------------------------------------------------
# Direct Answer Node
# -----------------------------------------------------------------------------

def direct_answer_handler(state: GraphState) -> GraphState:
    """
    Return a direct response without database query.

    Used for greetings, general chat, questions the LLM can answer directly.
    """
    user_input = state.get("user_input", "")
    plan = state.get("execution_plan")

    print(f"\n[NODE: direct_answer_handler]")
    print(f"User request: {user_input}")

    if plan and plan.response_text:
        # Use the pre-generated response from classification
        state["final_response"] = plan.response_text
    else:
        # Generate a conversational response
        system_prompt = """You are a friendly file management assistant.
The user has said something that doesn't require accessing their files.
Respond naturally and helpfully. Keep responses concise."""

        response = chat(system_prompt, user_input, temperature=0.7)  # <------- LLM CALL: direct answer
        state["final_response"] = response

    return state