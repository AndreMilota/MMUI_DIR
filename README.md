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

**3) Database quick test** – create/seed the database (if missing), then read a few rows.
```powershell
python scripts/db_smoketest.py
python scripts/db_query.py
```
Expected output: two rows that include `Sample1.mp3` and `Sample2.mp3`.

---

## Project layout (key parts)
```text
MMUI_DIR/
  app/
    __init__.py
    state.py
    runner.py
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
  file_scan/
    fs_database.py        # SQLite-backed file tracking database
    mock_file_system/
      mock_files.py       # mock file system for testing
      file_record_builder.py  # file record construction with defaults
  db/
    files.db              # created by db_smoketest.py
    memory/               # per-session JSON memory files
  scripts/
    hello_langgraph.py    # LangGraph hello
    test_groq.py          # Groq connectivity test
    db_smoketest.py       # create/seed table
    db_query.py           # read a few rows
    print_tree.py         # prints & copies folder tree
    visualize_graph.py    # ASCII + Mermaid graph
  docs/
    graph.md              # Mermaid diagram (generated)
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

### Running the tests

```powershell
python -m pytest file_scan/mock_file_system/test_mocks.py -v
python -m pytest file_scan/mock_file_system/test_file_record_builder.py -v
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

## Graph visualization

To print an ASCII map of the current LangGraph **and** write a Mermaid diagram to `docs/graph.md`:

```bash
python -m pip install -r requirements.txt   # includes grandalf
python scripts/visualize_graph.py
```

- The script prints an ASCII graph to the console (requires `grandalf`).
- It also writes a Mermaid diagram to `docs/graph.md` (GitHub renders it automatically).

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
