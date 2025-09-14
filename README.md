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
