# MMUI_DIR

Agent-based file-management experiments using **LangGraph** (workflow orchestration) and **Groq** (models).

---

## Requirements
- Python **3.12**
- A Groq API key in the environment variable **GROQ_API_KEY**

---

## Quick start (Windows PowerShell)

1) Create and activate a virtual environment:
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
Upgrade installer tools:

python -m pip install --upgrade pip wheel setuptools
Install project dependencies:

pip install -r requirements.txt
Set your Groq key
Option A — System environment (recommended):
Set GROQ_API_KEY in Windows so all shells and PyCharm can see it.

Option B — .env file (project-local):

Create a file named .env in the project root.

Put your key on one line (no quotes):

GROQ_API_KEY=your_actual_key_here
If you run from PyCharm, point the Run Configuration to this .env file:
Run → Edit Configurations… → Environment variables file (.env)

.env is already ignored by Git.

Verify the setup
1) Groq test (prints a short greeting)
python scripts/test_groq.py
2) LangGraph “hello”
powershell

hello_langgraph.py
3) Database quick test
Create/seed the database (if missing), then read a few rows.

python scripts/db_smoketest.py
python scripts/db_query.py
Expected output: two rows that include Sample1.mp3 and Sample2.mp3.

Project layout (key parts)
bash
Copy code
MMUI_DIR/
  app/
    __init__.py
    tools/
      __init__.py
      sql.py              # tiny helper for SQLite (db/files.db)
  db/
    files.db              # created by db_smoketest.py
  scripts/
    hello_langgraph.py    # LangGraph hello
    test_groq.py          # Groq connectivity test
    db_smoketest.py       # create/seed table
    db_query.py           # read a few rows
  .gitignore
  requirements.txt
  README.md
Notes
IDE settings (.idea/) and the virtual environment (.venv/) are ignored by Git.

The database file lives at db/files.db (project root).
The helper in app/tools/sql.py points there directly.

No graphical user interface is required to run these tests.

Troubleshooting
“GROQ_API_KEY is not set.”
Set the variable in Windows or use a project .env and link it in the Run Configuration. Restart PyCharm after changing system variables.

“no such table: files.”
Run python scripts/db_smoketest.py once to create and seed the table, then run python scripts/db_query.py again.

::contentReference[oaicite:0]{index=0}

## Folder tree utility (prints and copies the project layout)

We include a small helper at `scripts/print_tree.py` that prints a readable folder tree to the screen and, when possible, also copies the same text to your clipboard. This is useful when sharing the current project structure in chat or bug reports.

### What it does
- Prints a clean tree of the selected folders.
- Tries to copy the printed text to the clipboard on Windows, macOS, and Linux.
- Skips noisy folders by default: `.venv`, `.git`, `.idea`, `__pycache__`, `node_modules`, and files like `*.pyc`.

### How to run it (from the project root)

Windows PowerShell:
```powershell
python scripts/print_tree.py

macOS or Linux:

python3 scripts/print_tree.py


You will see the tree on screen. The script will also attempt to copy the same text to your clipboard and print a short note telling you if that worked.

Clipboard notes

Windows: uses the built-in clip command (no setup needed).

macOS: uses the built-in pbcopy command (no setup needed).

Linux: tries xclip or xsel. If neither is installed, you can install one of them, for example:

Debian/Ubuntu: sudo apt install xclip (or sudo apt install xsel)

Fedora: sudo dnf install xclip

Arch: sudo pacman -S xclip

Alternatively, install the pure-Python fallback:

pip install pyperclip


The script will use pyperclip automatically if it is available.

Options

Print the whole project (the . path) and limit depth to 6 levels:

python scripts/print_tree.py . --max-depth 6


Do not copy to the clipboard (print only):

python scripts/print_tree.py --no-copy


Exclude extra patterns (added to the default ignore list):

python scripts/print_tree.py . --exclude build dist *.log

Running from PyCharm

Right-click scripts/print_tree.py → Run 'print_tree'.

To set options, create a Run Configuration for this script and add arguments (for example: . --max-depth 6).
::contentReference[oaicite:0]{index=0}