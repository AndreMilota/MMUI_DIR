import subprocess
import sys
import os

def run_command(cmd, shell=True):
    """Run a command and exit on failure."""
    try:
        result = subprocess.run(cmd, shell=shell, check=True, capture_output=True, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running: {cmd}")
        print(e.stderr)
        sys.exit(1)

def main():
    print("Starting MMUI_DIR setup...")

    # Check if venv exists
    if not os.path.exists('.venv'):
        print("Creating virtual environment...")
        run_command("python -m venv .venv")

    # Activate venv (note: this may not work in all shells; user might need to re-run)
    print("Activating virtual environment (you may need to do this manually in your shell)...")
    # For Windows PowerShell
    if os.name == 'nt':
        run_command(". .\\.venv\\Scripts\\Activate.ps1", shell=False)  # May not work; suggest manual

    print("Upgrading installer tools...")
    run_command("python -m pip install --upgrade pip wheel setuptools")

    print("Installing dependencies...")
    run_command("pip install -r requirements.txt")

    print("Setup complete! Now set your GROQ_API_KEY and run verification scripts.")
    print("Example: python -m app.scripts.db_smoketest")

if __name__ == "__main__":
    main()
