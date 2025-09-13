# MMUI_DIR

Agent-based file management experiments using **LangGraph** and **Groq**.

## Requirements
- Python **3.12**
- A Groq API key in the environment variable **GROQ_API_KEY**

## Quick start (command line)

```bash
# 1) Create and activate a virtual environment (Windows PowerShell shown)
python -m venv .venv
. .\.venv\Scripts\Activate.ps1

# 2) Upgrade installer tools
python -m pip install --upgrade pip wheel setuptools

# 3) Install project dependencies
pip install -r requirements.txt

Set your Groq key

Either set it in your system environment or create a file named .env in the project root:

GROQ_API_KEY=your_actual_key_here


.env is already listed in .gitignore and will not be committed.

Verify the setup

Run the small test script (uses the OpenAI client pointed at Groq):

python test_groq.py


Expected: a short greeting printed to the console.