# MMUI_DIR

Agent-based file‑management experiments using **LangGraph** (workflow orchestration) and **Groq** (models).

---

## Requirements
- Python **3.12**
- `pip` 23+
- A Groq API key in the environment variable **`GROQ_API_KEY`**

---

## Quick start (Windows PowerShell)

1) **Create and activate a virtual environment**
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
```

2) **Upgrade installer tools**
```powershell
python -m pip install --upgrade pip wheel setuptools
```

3) **Install project dependencies**
```powershell
pip install -r requirements.txt
```

4) **Set your Groq key**

**Option A — System environment (recommended):** set `GROQ_API_KEY` in Windows so all shells and PyCharm can see it.

**Option B — `.env` file (project‑local):**
- Create a file named `.env` in the project root.
- Put your key on one line (no quotes):
  ```
  GROQ_API_KEY=your_actual_key_here
  ```
- If you run from PyCharm, point the Run Configuration to this `.env` file:  
  **Run → Edit Configurations… → Environment variables file (.env)**

> `.env` is already ignored by Git.

---

## Verify the setup

**1) Groq test (prints a short greeting)**
```powershell
python scripts/test_groq.py
```

**2) LangGraph “hello”**
```powershell
python scripts/hello_langgraph.py
```

**3) Mock file-system smoke test** – creates a `MockFiles` instance, saves a file, and prints a directory listing with human-readable timestamps.
```powershell
python -m scripts.simple_agent_tests
```
Expected output: one row showing `beatles_best_of.mp3` with size and created/modified timestamps.

**4) Database quick test** – create/seed the database (if missing), then read a few rows.
```powershell
python scripts/db_smoketest.py
python scripts/db_query.py
```
Expected output: two rows that include `Sample1.mp3` and `Sample2.mp3`.

---

## Project layout (key parts)
```text
MMUI_DIR/
  app/                    # Original linear LangGraph workflow
    __init__.py
    state.py
    runner.py
    graph.py              # Linear: text_to_sql → execute_sql → sql_to_text
    llm/
      core.py             # Groq LLM wrapper (chat, chat_json)
    utils/
      __init__.py
      clipboard.py        # print_copy() for accessibility (prints + copies to clipboard)
    orchestrator/
      __init__.py
      graph.py
      router.py
      planner_llm.py
      modes/
        __init__.py
        ui.py
        data.py
        agent.py
    tools/
      __init__.py
      sql.py              # tiny helper for SQLite (db/files.db)
  app_2/                  # Branching LangGraph workflow
    __init__.py
    state.py              # GraphState, ExecutionPlan, ActionType enum
    graph.py              # Branching graph with conditional routing
    nodes.py              # Classification + 9 processing nodes; modular prompt components
    runner.py             # Entry point: run_query(user_input, now, db_path, file_system)
    path_guard.py         # Permission-based path access control (PathGuard, TODO: integrate)
  file_scan/
    fs_reader.py          # FSReader ABC + RealFSReader (OS-level file iteration)
    fs_database.py        # SQLite-backed file tracking database
    fs_load.py            # scan_path_into_db() — ties reader + database together
    mock_file_system/
      mock_files.py       # MockFiles: virtual filesystem for testing
      mock_fs_reader.py   # MockFSReader — FSReader adapter for MockFiles
      file_record_builder.py  # file record construction with defaults
      test_fs_reader_using_mocks.py  # end-to-end scan test using MockFSReader
    tests/
      export_db.py        # export database tables to TSV files
  db/
    files.db              # created by db_smoketest.py
    memory/               # per-session JSON memory files
  scripts/
    print_tree.py             # prints & copies folder tree (standalone)
    clean_temp_files.py       # delete .tsv and .sqlite temp files (standalone)
    app/                      # Tests and scripts for app (original workflow)
      simple_agent_tests.py   # MockFiles smoke test with directory listing
      run_graph_once.py       # Run the linear graph once
      db_query.py             # Read a few rows from the database
    app_2/                    # Tests for app_2 branching workflow (one file per branch)
      branching_agent_tests.py    # Coordinator — calls all per-branch test files
      test_query_respond.py       # query_respond branch tests
      test_query_display.py       # query_display branch tests
      test_query_store.py         # query_store branch tests
      test_query_transform.py     # query_transform branch tests (move/rename/delete)
      test_query_copy.py          # query_copy branch tests (including sync copy)
      test_query_feed_llm.py      # query_feed_llm branch tests (SQL escalation)
      test_query_external.py      # query_external branch tests
      test_web_search.py          # web_search branch tests
      test_direct_answer.py       # direct_answer branch tests
      visualize_graph.py          # Generate Mermaid diagram of the workflow
    docs/
      branching_graph.md      # Mermaid diagram + action type reference
      graph.md                # Original graph diagram
      path_guard.md           # PathGuard design notes
  CLAUDE.md               # Coding conventions for Claude Code sessions
  .gitignore
  requirements.txt
  README.md
```

---

## Mock File System (for testing)

The `file_scan/mock_file_system` module provides a mock file system that wraps `FSDatabase` for testing purposes. It lets you create realistic file system states in a SQLite database without touching the real file system.

### Key difference from a real file system

The file tracking database retains records of all files it has seen, even after deletion. This lets you simulate scenarios like:
1. File existed, was scanned into the database
2. File was deleted
3. Re-scan shows the file as "missing" but the record remains

### Basic usage

```python
from file_scan.mock_file_system.mock_files import MockFiles

# Create a mock file system (uses an in-memory or file-based SQLite DB)
mock_fs = MockFiles(":memory:")  # or provide a path like "test.db"

# Mount a volume (auto-generates drive letter C, D, E... and serial numbers)
mock_fs.mount_volume()                          # Creates C:\
mock_fs.mount_volume()                          # Creates D:\
mock_fs.mount_volume(drive_letter='Z', label='USB')  # Creates Z:\

# Directory operations
mock_fs.mkdir("C:\\Users\\Bob\\Documents")      # Creates all parent dirs
mock_fs.cd("C:\\Users\\Bob")                    # Change directory
print(mock_fs.getcwd())                         # "C:\Users\Bob"
mock_fs.ls_dir()                                # List subdirectory names in cwd

# Create files
mock_fs.save("report.txt", size_bytes=1024)
mock_fs.save("photo.jpg", size_bytes=2048000)
mock_fs.ls()                                    # List files in cwd (returns list of dicts)

# Pretty-print a directory listing (returns formatted multi-line string)
listing = mock_fs.dir("C:\\Users\\Bob")
print(listing)
# dir: C:\Users\Bob
#   [Documents/]
#   photo.jpg
#   report.txt
print(f"  ({len(listing.splitlines()) - 1} items)")  # count entries (subtract header line)
```

### File defaults (sticky parameters)

When you specify a parameter, it becomes the new default for subsequent files:

```python
# Set defaults explicitly
mock_fs.set_file_defaults(extension='txt', size_bytes=1024)

# Or let them "stick" from previous save() calls
mock_fs.save("first.pdf", size_bytes=2048)
mock_fs.save("second")      # Uses extension='pdf', size_bytes=2048
mock_fs.save("third")       # Same defaults continue
```

### Human-readable timestamps

Time parameters accept multiple formats:

```python
from datetime import datetime, date, time

# ISO format strings
mock_fs.save("log.txt", mtime="2024-01-15 10:30:00")
mock_fs.save("log.txt", mtime="2024-01-15")        # Uses default time (00:00:00)
mock_fs.save("log.txt", mtime="10:30:00")          # Uses default date (2000-01-01)

# Python datetime objects
mock_fs.save("log.txt", mtime=datetime(2024, 1, 15, 10, 30))
mock_fs.save("log.txt", mtime=date(2024, 1, 15))
mock_fs.save("log.txt", mtime=time(10, 30))

# Set default date/time for partial specifications
mock_fs.set_file_defaults(default_date="2024-06-01", default_time="12:00:00")
```

### Media and tag metadata

Files can include media metadata and ID3-style tags:

```python
mock_fs.save(
    "song.mp3",
    duration=180.5,
    bitrate=320000,
    codec='mp3',
    sample_rate=44100,
    channels=2,
    tag_title="My Song",
    tag_artist="Artist Name",
    tag_album="Album Title"
)
```

### Mock clock (auto-advancing time)

`MockFiles` includes a mock clock that starts at `2025-01-01 00:00:00` and
auto-advances by **1 second** every time a filesystem-modifying operation
completes (`save`, `mkdir`, `rmdir`, `delete`, `set_attributes`, `copy`,
`move`, `copydir`, `movedir`).

When a file is created with `save()` and no `mtime`/`ctime` is specified
(either explicitly or via a sticky default), the mock clock provides the
timestamp.

**Priority order for timestamps:**
1. Explicit kwarg in the `save()` call (also becomes the sticky default)
2. Sticky default (non-`None`) set via `set_file_defaults()`
3. Mock clock value (used when neither of the above is set)

```python
mock_fs = MockFiles(":memory:")
mock_fs.mount_volume()

# Read / set / increment the clock
print(mock_fs.get_time())                   # nanoseconds since epoch
mock_fs.set_time("2025-06-15 12:00:00")     # accepts string or int (ns)
mock_fs.increment_time(5_000_000_000)       # advance by 5 seconds

# Auto-advancing: each save() advances by 1 second
mock_fs.set_time("2025-01-01 00:00:00")
mock_fs.save("file1.txt")   # gets mtime/ctime = 2025-01-01 00:00:00
mock_fs.save("file2.txt")   # gets mtime/ctime = 2025-01-01 00:00:01
mock_fs.save("file3.txt")   # gets mtime/ctime = 2025-01-01 00:00:02
```

### MockFSReader — scanning a mock file system

`MockFSReader` is an `FSReader` adapter that lets `scan_path_into_db()` scan a
`MockFiles` instance through the exact same code path used for the real OS.
This means tests exercise the full scan pipeline (volume upsert, directory
iteration, file upsert, presence-state tracking) without touching the real
file system.

```python
from file_scan.mock_file_system.mock_files import MockFiles
from file_scan.mock_file_system.mock_fs_reader import MockFSReader
from file_scan.fs_load import scan_path_into_db

# Build a virtual filesystem
vfs = MockFiles("test_vfs.sqlite")
vfs.set_time("2026-01-01 12:00:00")
vfs.mount_volume(drive_letter='C')
vfs.mkdir("C:\\data")
vfs.cd("C:\\data")
vfs.save("report.txt", size_bytes=512)

# Scan it into a separate database — just like scanning a real directory
reader = MockFSReader(vfs)
scan_db = scan_path_into_db("C:\\data", "scan_output.sqlite", reader=reader)
```

You can also create a `MockFSReader` directly from an existing MockFiles
database file:

```python
reader = MockFSReader.from_file("test_vfs.sqlite")
# The clock is automatically set past the latest file timestamp
```

### Scan timestamps (`now()`)

Every `FSReader` has a `now()` method that returns the current time in
nanoseconds. The scan loop in `fs_load.py` calls `reader.now()` to populate
the `last_scan_started_ns` and `last_scan_completed_ns` columns on each
directory row:

- **`RealFSReader.now()`** — returns wall-clock time via `time.time_ns()`.
- **`MockFSReader.now()`** — reads the MockFiles clock, then auto-advances it
  by 1 second. Each call returns a unique, sequential timestamp.

This guarantees that scan timestamps are always chronologically after all
file-creation timestamps in the mock, avoiding time paradoxes in tests.

**Timestamp flow example** (MockFiles clock at `2026-01-01 12:00:00`, then
5 files saved, then `mkdir`):

| Step | Clock reads | Column written |
|------|------------|---------------|
| Files created (5 saves) | 12:00:01 – 12:00:05 | `mtime_ns` / `ctime_ns` on files |
| `mkdir` | 12:00:06 | *(clock advances)* |
| `reader.now()` for scan start | 12:00:06 → clock becomes 12:00:07 | `last_scan_started_ns` |
| Files iterated | *(read-only, no clock change)* | |
| `reader.now()` for scan end | 12:00:07 → clock becomes 12:00:08 | `last_scan_completed_ns` |

### Running a real scan

`fs_load.py` scans a real directory and writes results (including scan
timestamps) to a SQLite database. It can be run as a module or directly:

```powershell
python -m file_scan.fs_load                          # scans ~/Downloads by default
python -m file_scan.fs_load "C:\Users\owner\Music"   # scan a specific path
```

You can also run the file directly from PyCharm or the command line:
```powershell
python file_scan/fs_load.py
```

After scanning, use `export_db.py` (see below) to inspect the results with
human-readable timestamps.

### Running the tests

```powershell
python -m pytest file_scan/mock_file_system/test_mocks.py -v
python -m pytest file_scan/mock_file_system/test_file_record_builder.py -v
```

**End-to-end scan test** — exercises MockFSReader + `scan_path_into_db`, verifies
presence-state tracking and scan timestamp ordering:
```powershell
python -m file_scan.mock_file_system.test_fs_reader_using_mocks
```

---

## Branching LangGraph Workflow (app_2)

The `app_2` module implements a branching LangGraph workflow that classifies user intent and routes to specialized processing nodes. This is the foundation for the multimodal file manager agent.

### Architecture

```
                    ┌─────────────────┐
                    │    classify     │
                    │  (LLM call to   │
                    │ determine intent│
                    │ + generate SQL) │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌─────────┐   ┌───────────┐   ┌──────────┐
        │ execute │   │  web_     │   │ direct_  │
        │   sql   │   │  search   │   │ answer   │
        │ (7 var) │   │  (stub)   │   │          │
        └────┬────┘   └─────┬─────┘   └────┬─────┘
             │              │              │
     ┌───────┴───────┐      │              │
     ▼               ▼      │              │
┌─────────┐   ┌──────────┐  │              │
│ respond │   │transform │  │              │
│ display │   │  copy    │  │              │
│ store   │   │ feed_llm │  │              │
│         │   │ external │  │              │
└────┬────┘   └────┬─────┘  │              │
     │             │        │              │
     └─────────────┴────────┴──────────────┘
                             │
                             ▼
                          [END]
```

### Action Types (Branches)

| Action Type | Purpose | SQL Required | Status |
|-------------|---------|--------------|--------|
| `query_respond` | Single value → natural language | Yes | Implemented |
| `query_display` | Show table to user | Yes | Implemented |
| `query_store` | Store table for multi-turn dialog | Yes | Implemented |
| `query_transform` | Move/rename/delete files | Yes (source/dest) | VFS Implemented |
| `query_copy` | Copy files | Yes (source/dest) | VFS Implemented |
| `query_feed_llm` | AI processing of file data | Yes | Stub |
| `query_external` | Run external app per file | Yes | Stub |
| `web_search` | Web research (not file-related) | No | Stub |
| `direct_answer` | Conversational responses | No | Implemented |

> **Note:** `query_transform` and `query_copy` use the virtual filesystem (MockFiles) for testing. Real filesystem operations are disabled until PathGuard integration is complete.

### Usage

```python
from app_2 import run_query

# Single value query
result = run_query(
    "How many MP3 files do I have?",
    now="2026-02-15 12:00:00",
    db_path="test.sqlite"
)
print(result['final_response'])  # "You have 5 MP3 files."
print(result['action_type'])      # "query_respond"

# File operations (stub)
result = run_query(
    "Delete all .tmp files in C:/Downloads/Temp",
    now="2026-02-15 12:00:00",
    db_path="test.sqlite"
)
# Prints planned operations table with source_path and dest_path columns

# Conversational
result = run_query("Hello, how are you?", db_path="test.sqlite")
print(result['final_response'])  # Friendly greeting response
```

### Running the tests

Each branch has its own test file that can be run standalone or via the coordinator:

```powershell
# Run all branch tests (coordinator)
python -m scripts.app_2.branching_agent_tests

# Run a single branch's tests
python -m scripts.app_2.test_query_display
python -m scripts.app_2.test_query_copy
python -m scripts.app_2.test_query_transform
# etc.
```

### Key Files

| File | Purpose |
|------|---------|
| `app_2/state.py` | `ActionType` enum, `ExecutionPlan` Pydantic model, `GraphState` TypedDict |
| `app_2/nodes.py` | Classification node + all processing nodes; modular prompt components |
| `app_2/graph.py` | Graph construction with conditional routing |
| `app_2/runner.py` | `run_query(user_input, now, db_path, file_system)` entry point |

### ExecutionPlan Model

The classification LLM returns a structured `ExecutionPlan`:

```python
class ExecutionPlan(BaseModel):
    action_type: ActionType      # Which branch to take
    sql: Optional[str]           # SQL query (if needed)
    processing_instruction: str  # What to do with results
    response_text: Optional[str] # For direct_answer
    llm_instruction: Optional[str]  # For query_feed_llm
    external_app: Optional[str]  # For query_external
    reasoning: str               # Why this classification
```

For file operations (`query_transform`, `query_copy`), the SQL must return:
- `source_path`: Full path of the file
- `dest_path`: Destination path (or NULL for delete)

### GraphState Fields for File Operations

| Field | Type | Purpose |
|-------|------|---------|
| `file_system` | MockFiles (or real adapter) | Filesystem instance passed in from the caller |
| `use_real_fs` | bool | Safety flag — always `False` until PathGuard is integrated |
| `operation_results` | List[Dict] | Per-file success/failure results |
| `operation_errors` | List[str] | Error messages from failed operations |

The node detects whether the filesystem is real by checking `isinstance(file_system, MockFiles)`. If it is real and `use_real_fs` is `False`, the operation is blocked and an error is returned. This prevents accidental real-filesystem writes during testing.

---

## Exporting the scan database to TSV

`file_scan/tests/export_db.py` exports the three scan-database tables
(`volumes`, `directories`, `files`) to tab-delimited `.tsv` files you can
open in Excel or any spreadsheet program.

```powershell
python -m file_scan.tests.export_db                        # default DB (file_scan/file_database.sqlite)
python -m file_scan.tests.export_db path\to\other.sqlite   # explicit DB path
```

By default, all nanosecond timestamp columns (`mtime_ns`, `ctime_ns`,
`last_scan_started_ns`, `last_scan_completed_ns`) are exported as
human-readable datetime strings (e.g. `2026-01-07 22:16:54`) and the
`_ns` suffix is stripped from the column header.

To keep the raw nanosecond integers and original column names:

```powershell
python -m file_scan.tests.export_db --raw-timestamps
```

The `export_table_to_tsv` function also accepts a `raw_timestamps` keyword
argument for programmatic use:

```python
from file_scan.tests.export_db import export_table_to_tsv

export_table_to_tsv(conn, "files", Path("files.tsv"))                    # human-readable (default)
export_table_to_tsv(conn, "files", Path("files.tsv"), raw_timestamps=True)  # raw nanoseconds
```

---

## Folder tree utility (prints and copies the project layout)

We include a helper at `scripts/print_tree.py` that prints a readable folder tree to the screen and, when possible, also copies the same text to your clipboard.

### How to run (from the project root)
**Windows PowerShell**
```powershell
python scripts/print_tree.py
```

**macOS or Linux**
```bash
python3 scripts/print_tree.py
```

You will see the tree on screen. The script also attempts to copy the same text to your clipboard and prints a short note telling you if that worked.

### Clipboard notes
- **Windows:** uses the built‑in `clip` command (no setup needed).
- **macOS:** uses the built‑in `pbcopy` command (no setup needed).
- **Linux:** tries `xclip` or `xsel`. If neither is installed, you can install one of them, for example:
  - Debian/Ubuntu: `sudo apt install xclip` (or `sudo apt install xsel`)
  - Fedora: `sudo dnf install xclip`
  - Arch: `sudo pacman -S xclip`

  Alternatively, install the pure‑Python fallback:
  ```bash
  pip install pyperclip
  ```
  The script will use `pyperclip` automatically if it is available.

### Options
- Print the whole project (the `.` path) and limit depth to 6 levels:
  ```bash
  python scripts/print_tree.py . --max-depth 6
  ```
- Do not copy to the clipboard (print only):
  ```bash
  python scripts/print_tree.py --no-copy
  ```
- Exclude extra patterns (added to the default ignore list):
  ```bash
  python scripts/print_tree.py . --exclude build dist *.log
  ```

### Running from PyCharm
- Right‑click `scripts/print_tree.py` → **Run 'print_tree'**.
- To set options, create a Run Configuration and add arguments (for example: `. --max-depth 6`).

---

## Cleaning up temporary files

Test scripts and scan operations create `.tsv` (tab-separated exports) and `.sqlite` database files throughout the project. These are already git-ignored, but they can accumulate. Use `clean_temp_files.py` to remove them.

```powershell
python -m scripts.clean_temp_files            # list files and confirm before deleting
python -m scripts.clean_temp_files --dry-run  # list files without deleting
python -m scripts.clean_temp_files --yes      # delete without confirmation
```

---

## Accessibility utilities

The `print_copy()` function in `app/utils/clipboard.py` prints text to stdout AND copies it to the clipboard. This is useful for users with screen readers or speech synthesizers that monitor the clipboard.

```python
from app.utils.clipboard import print_copy

print_copy("Query completed: 15 files found")  # prints AND copies
```

The `app_2` runner uses `print_copy()` for user requests and system responses.

---

## Coding conventions (CLAUDE.md)

The `CLAUDE.md` file in the project root documents coding patterns for AI-assisted development sessions:

- **Marker comments**: Important operations are marked with `# <------- CATEGORY: description`
  ```python
  response = chat(system_prompt, user_prompt)  # <------- LLM CALL: classify intent
  cursor.execute(sql)  # <------- DATABASE QUERY
  vfs.move(source, dest)  # <------- FILE OPERATION: move
  ```

- **Modular prompt components**: LLM prompt guidance is stored in module-level variables for A/B testing, conditional inclusion, and future RAG retrieval. Current variables in `app_2/nodes.py`:
  - `SQL_ESCALATION_GUIDANCE` — when SQL can handle a transform vs when to escalate to `query_feed_llm`
  - `DEFAULT_SCOPE_GUIDANCE` — default to current directory only (no subdirs) unless user says otherwise; reusable across all query branches
  - `QUERY_DISPLAY_GUIDANCE` — display formatting rules: human-readable timestamps, filename-only column when a single directory is pinned, separate path + filename columns when results span multiple directories

- **Virtual filesystem testing**: File operations use `MockFiles` for testing with explicit checks to prevent accidental real filesystem access. Pass the `MockFiles` instance via the `file_system` parameter of `run_query()`.

---

## Graph visualization

To generate a visual diagram of the app_2 branching workflow:

```bash
python -m app_2.visualize_graph
```

This creates:
- `app_2/graph_diagram.mmd` — Mermaid diagram (paste at https://mermaid.live to view)
- `app_2/graph_diagram.png` — PNG image (if graphviz/pygraphviz is installed)

The Mermaid output is also printed to the console.

---

## Troubleshooting

**“GROQ_API_KEY is not set.”**  
Set the variable in Windows or use a project `.env` and link it in the Run Configuration. Restart PyCharm after changing system variables.

**“no such table: files.”**  
Run `python scripts/db_smoketest.py` once to create and seed the table, then run `python scripts/db_query.py` again.

**Imports fail when running a script under `scripts/`**  
Either run as a module:
```bash
python -m scripts.run_llm_routing_demo
```
or add this to the top of the script (before other imports):
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
```

---

## License
MIT (see `LICENSE`).
