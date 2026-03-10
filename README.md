# MMUI_DIR

Agent-based file‑management experiments using **LangGraph** (workflow orchestration) and **Groq** (models).

---

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Verification](#verification)
- [Project Structure](#project-structure)
- [Utilities](#utilities)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Prerequisites

### System Requirements
- Python **3.12**
- `pip` 23+

### API Access
- A Groq API key (stored in environment variable **`GROQ_API_KEY`**)
- Get your free API key at [groq.com](https://groq.com)
  - Login or create an account and follow the instructions

---

## Installation
There are three ways to handle the installation: automated, manual, or quick start. They should all accomplish the same thing, and all need to be updated if the project changes.

### Automated Setup (Recommended)
Run the automated setup script for a quick start:

```powershell
python -m app.scripts.setup
```

This handles venv creation, activation, upgrades, and dependency installation. After running, proceed to [Configuration](#configuration).

### Quick Setup Script (Inline)
For convenience, you can copy and run this entire PowerShell script manually (replace `your_actual_key_here` with your actual Groq API key):

```powershell
# Create and activate virtual environment
python -m venv .venv
. .\.venv\Scripts\Activate.ps1

# Upgrade installer tools
python -m pip install --upgrade pip wheel setuptools

# Install project dependencies
pip install -r requirements.txt

# Set Groq key (uncomment and modify one of the options below)
# Option A: Set system environment variable (run in elevated PowerShell if needed)
# [Environment]::SetEnvironmentVariable("GROQ_API_KEY", "your_actual_key_here", "Machine")

# Option B: Create .env file
# New-Item -ItemType File -Path .env -Force
# Set-Content -Path .env -Value "GROQ_API_KEY=your_actual_key_here"

# Set up database
python -m app.scripts.db_smoketest

# Verify setup
python -m app.scripts.test_groq
python -m app.scripts.hello_langgraph
python -m app.scripts.db_query
```

### Manual Setup
If you prefer manual steps or need to customize:

#### Step 1: Create Virtual Environment
**Important:** Always activate the virtual environment before running any Python scripts or commands to ensure dependencies are available.

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
```

#### Step 2: Upgrade Installer Tools
```powershell
python -m pip install --upgrade pip wheel setuptools
```

#### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```



---

## Configuration

### Setting Your Groq API Key

#### Option A: System Environment Variable (Recommended)
Set `GROQ_API_KEY` in Windows system environment variables so all shells and PyCharm can access it.

#### Option B: Project-Local `.env` File
1. Create a file named `.env` in the project root
2. Add your key on one line (no quotes):
   ```
   GROQ_API_KEY=your_actual_key_here
   ```
3. For PyCharm users: Configure the Run Configuration to use this `.env` file
   - Navigate to **Run → Edit Configurations… → Environment variables file (.env)**

> Note: `.env` is already ignored by Git for security.

---

## Database Setup

### Initialize Database
Create and seed the database with sample data:

```powershell
python -m app.scripts.db_smoketest
```

This creates `db/files.db` with sample records if it doesn't already exist.

---

## Verification

### Test Individual Components

#### 1. Groq Connectivity Test
Prints a short greeting to verify API connection:
```powershell
python -m app.scripts.test_groq
```

#### 2. LangGraph Test
Runs a basic "hello" workflow:
```powershell
python -m app.scripts.hello_langgraph
```

#### 3. Mock file-system smoke test** – creates a `MockFiles` instance, saves a file, and prints a directory listing with human-readable timestamps.
```powershell
python -m scripts.simple_agent_tests
```
Expected output: one row showing `beatles_best_of.mp3` with size and created/modified timestamps.

**4) Database Query Test
Reads sample rows from the database:
```powershell
python -m app.scripts.db_query
```

**Expected output:** Two rows containing `Sample1.mp3` and `Sample2.mp3`.

---

## Project Structure

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
    scripts/
      db_smoketest.py       # create/seed table
      db_query.py           # read a few rows
      hello_langgraph.py    # LangGraph hello
      test_groq.py          # Groq connectivity test
      print_tree.py         # prints & copies folder tree
      visualize_graph.py    # ASCII + Mermaid graph
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
  app_2/                  # NEW: Branching LangGraph workflow
    __init__.py
    state.py              # GraphState, ExecutionPlan, ActionType enum
    graph.py              # Branching graph with conditional routing
    nodes.py              # Classification + 9 processing nodes
    runner.py             # Entry point: run_query()
    path_guard.py         # Permission-based path access control
    visualize_graph.py    # Generate Mermaid diagram of the workflow
  file_scan/
    fs_reader.py          # FSReader ABC + RealFSReader (OS-level file iteration)
    fs_database.py        # SQLite-backed file tracking database
    fs_load.py            # scan_path_into_db() — ties reader + database together
    mock_file_system/
      mock_files.py       # mock file system for testing
      mock_fs_reader.py   # MockFSReader — FSReader adapter for MockFiles
      file_record_builder.py  # file record construction with defaults
      test_fs_reader_using_mocks.py  # end-to-end scan test using MockFSReader
    tests/
      export_db.py        # export database tables to TSV files
  db/
    files.db              # created by db_smoketest.py
    memory/               # per-session JSON memory files
  scripts/
    hello_langgraph.py        # LangGraph hello
    test_groq.py              # Groq connectivity test
    db_smoketest.py           # create/seed table
    db_query.py               # read a few rows
    print_tree.py             # prints & copies folder tree
    simple_agent_tests.py     # MockFiles smoke test with directory listing
    branching_agent_tests.py  # Tests for app_2 branching workflow
    sql_escalation_test.py    # Tests for SQL vs LLM routing decisions
    display_sorting_tests.py  # Tests for query_display sorting/grouping
    clean_temp_files.py       # delete .tsv and .sqlite temp files
  docs/
    graph.md              # Mermaid diagram (generated)
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
mock_fs.ls_dir()                                # List subdirectories

# Create files
mock_fs.save("report.txt", size_bytes=1024)
mock_fs.save("photo.jpg", size_bytes=2048000)
mock_fs.ls()                                    # List files in cwd
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

```powershell
# Run all branching agent tests
python -m scripts.branching_agent_tests

# SQL escalation tests (verifies SQL vs LLM routing decisions)
python -m scripts.sql_escalation_test

# Display sorting/grouping tests
python -m scripts.display_sorting_tests
```

### Key Files

| File | Purpose |
|------|---------|
| `app_2/state.py` | `ActionType` enum, `ExecutionPlan` Pydantic model, `GraphState` TypedDict |
| `app_2/nodes.py` | Classification node + all processing nodes |
| `app_2/graph.py` | Graph construction with conditional routing |
| `app_2/runner.py` | `run_query()` entry point |

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
| `vfs` | MockFiles | Virtual filesystem instance for testing |
| `use_real_fs` | bool | If True, use real FS (disabled until PathGuard ready) |
| `operation_results` | List[Dict] | Per-file success/failure results |
| `operation_errors` | List[str] | Error messages from failed operations |

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

## Utilities

### Folder Tree Printer

The `print_tree.py` utility prints a readable folder tree and copies it to your clipboard.

#### Basic Usage
```powershell
python -m app.scripts.print_tree
```

#### Platform-Specific Clipboard Support
- **Windows:** Uses built‑in `clip` command (no setup needed)
- **macOS:** Uses built‑in `pbcopy` command (no setup needed)
- **Linux:** Requires `xclip` or `xsel`
  - Debian/Ubuntu: `sudo apt install xclip`
  - Fedora: `sudo dnf install xclip`
  - Arch: `sudo pacman -S xclip`
  - **Alternative:** Install pure‑Python fallback: `pip install pyperclip`

#### Advanced Options

**Limit tree depth:**
```bash
python -m app.scripts.print_tree . --max-depth 6
```

**Print only (skip clipboard):**
```bash
python -m app.scripts.print_tree --no-copy
```

**Exclude additional patterns:**
```bash
python -m app.scripts.print_tree . --exclude build dist *.log
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

- **Modular prompt components**: LLM prompt guidance is stored in module-level variables (e.g., `SQL_ESCALATION_GUIDANCE`) for A/B testing and conditional inclusion.

- **Virtual filesystem testing**: File operations use MockFiles for testing with explicit checks to prevent accidental real filesystem access.

---

## Graph visualization

To generate a visual diagram of the app_2 branching workflow:

```bash
python -m pip install -r requirements.txt   # includes grandalf
python -m app.scripts.visualize_graph
```

#### Output
- **Console:** ASCII graph visualization (requires `grandalf`)
- **File:** Mermaid diagram written to `docs/graph.md` (auto-renders on GitHub)

---

## Troubleshooting

### Common Issues

#### "GROQ_API_KEY is not set"
**Solution:** Set the environment variable in Windows or create a `.env` file and link it in your Run Configuration. Restart PyCharm after changing system environment variables.

#### "no such table: files"
**Solution:** Run the database setup script:
```bash
python -m app.scripts.db_smoketest
```
Then retry your query:
```bash
python -m app.scripts.db_query
```

#### Import errors when running scripts
**Solution:** Run scripts as modules:
```bash
python -m app.scripts.run_llm_routing_demo
```

**Alternative:** Add this to the top of the script (before other imports):
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
```

---

## License

MIT (see `LICENSE`).
