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

#### 3. Database Query Test
Reads sample rows from the database:
```powershell
python -m app.scripts.db_query
```

**Expected output:** Two rows containing `Sample1.mp3` and `Sample2.mp3`.

---

## Project Structure

```text
MMUI_DIR/
  app/
    __init__.py
    state.py
    runner.py
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
  db/
    files.db              # created by db_smoketest.py
    memory/               # per-session JSON memory files
  docs/
    graph.md              # Mermaid diagram (generated)
  .gitignore
  requirements.txt
  README.md
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

#### Running from PyCharm
- Right‑click `app/scripts/print_tree.py` → **Run 'print_tree'**
- To set options, create a Run Configuration and add arguments (e.g., `. --max-depth 6`)

---

### Graph Visualization

Generate both ASCII and Mermaid diagrams of the LangGraph workflow.

#### Setup and Run
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
