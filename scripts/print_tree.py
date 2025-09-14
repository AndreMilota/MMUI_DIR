# scripts/print_tree.py
"""
Print a readable folder tree and (optionally) copy it to the clipboard.

Usage (from project root or via PyCharm Run):
  python scripts/print_tree.py
    - Prints sections for 'app', 'scripts', and 'db' if they exist
    - Tries to copy the same text to the clipboard

  python scripts/print_tree.py --no-copy
    - Prints only; do not copy

  python scripts/print_tree.py . --max-depth 6
    - Print the whole project tree up to a certain depth

Notes:
- On Windows we use the 'clip' command.
- On macOS we use 'pbcopy'.
- On Linux we try 'xclip' or 'xsel'. If neither is installed, install one or
  install 'pyperclip' (pip install pyperclip), which also works cross-platform.
- We exclude noisy folders by default: .venv, .git, .idea, __pycache__, node_modules, *.pyc
"""

from __future__ import annotations
import argparse
import os
import platform
import shutil
import subprocess
from pathlib import Path
from fnmatch import fnmatch

DEFAULT_SECTIONS = ["app", "scripts", "db"]
DEFAULT_EXCLUDES = {
    ".venv", ".git", ".idea", "__pycache__", "node_modules", "*.pyc", "*.pyo",
}

ASCII = {
    "tee": "+-- ",
    "elbow": "\\-- ",
    "pipe": "|   ",
    "space": "    ",
}

def build_tree_lines(root: Path, max_depth: int | None, excludes: list[str]) -> list[str]:
    """Return a list of lines showing the tree rooted at 'root'."""
    lines: list[str] = []

    def is_excluded(p: Path) -> bool:
        name = p.name
        # Match by name and by simple glob on the path relative to the printed root
        try:
            rel = str(p.relative_to(root))
        except ValueError:
            rel = name
        for pat in excludes:
            if fnmatch(name, pat) or fnmatch(rel, pat):
                return True
        return False

    def walk(dir_path: Path, prefix: str, depth: int):
        if max_depth is not None and depth > max_depth:
            return
        try:
            entries = [e for e in dir_path.iterdir() if not is_excluded(e)]
        except PermissionError:
            lines.append(prefix + "[permission denied]")
            return
        entries.sort(key=lambda e: (not e.is_dir(), e.name.lower()))
        last_index = len(entries) - 1

        for idx, entry in enumerate(entries):
            connector = ASCII["elbow"] if idx == last_index else ASCII["tee"]
            lines.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                extension = ASCII["space"] if idx == last_index else ASCII["pipe"]
                walk(entry, prefix + extension, depth + 1)

    # Header
    lines.append(str(root.resolve()))
    if root.exists():
        walk(root, "", 1)
    else:
        lines.append("(does not exist)")
    return lines

def copy_to_clipboard(text: str) -> tuple[bool, str]:
    """Try several cross-platform clipboard methods. Return (success, note)."""
    # 1) Try pyperclip if available
    try:
        import pyperclip  # type: ignore
        pyperclip.copy(text)
        return True, "Copied to clipboard via pyperclip."
    except Exception:
        pass

    system = platform.system()

    # 2) Windows 'clip'
    if system == "Windows":
        if shutil.which("clip"):
            try:
                subprocess.run(["clip"], input=text, text=True, check=True)
                return True, "Copied to clipboard via Windows 'clip'."
            except Exception as e:
                return False, f"Clipboard copy failed with 'clip': {e}"
        return False, "Windows 'clip' not found."

    # 3) macOS 'pbcopy'
    if system == "Darwin":
        if shutil.which("pbcopy"):
            try:
                subprocess.run(["pbcopy"], input=text, text=True, check=True)
                return True, "Copied to clipboard via macOS 'pbcopy'."
            except Exception as e:
                return False, f"Clipboard copy failed with 'pbcopy': {e}"
        return False, "macOS 'pbcopy' not found."

    # 4) Linux 'xclip' or 'xsel'
    if system == "Linux":
        if shutil.which("xclip"):
            try:
                subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, check=True)
                return True, "Copied to clipboard via Linux 'xclip'."
            except Exception as e:
                return False, f"Clipboard copy failed with 'xclip': {e}"
        if shutil.which("xsel"):
            try:
                subprocess.run(["xsel", "-b", "-i"], input=text, text=True, check=True)
                return True, "Copied to clipboard via Linux 'xsel'."
            except Exception as e:
                return False, f"Clipboard copy failed with 'xsel': {e}"
        return False, "Neither 'xclip' nor 'xsel' found on Linux."

    return False, f"Unsupported platform: {system}"

def main():
    parser = argparse.ArgumentParser(description="Print a folder tree and optionally copy it to the clipboard.")
    parser.add_argument("paths", nargs="*", help="Folders to include. Default: app, scripts, db if present; otherwise project root.")
    parser.add_argument("--max-depth", type=int, default=None, help="Limit tree depth (example: 6). Default: no limit.")
    parser.add_argument("--no-copy", action="store_true", help="Do not attempt clipboard copy.")
    parser.add_argument("--exclude", nargs="*", default=[], help="Extra patterns to exclude (in addition to defaults).")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    selections = args.paths if args.paths else [p for p in DEFAULT_SECTIONS if (project_root / p).exists()]
    if not selections:
        selections = ["."]
    excludes = list(DEFAULT_EXCLUDES) + args.exclude

    sections_output: list[str] = []
    for section in selections:
        root = (project_root / section).resolve()
        sections_output.append(f"=== {section} ===")
        sections_output.extend(build_tree_lines(root, args.max_depth, excludes))
        sections_output.append("")

    output_text = "\n".join(sections_output).rstrip()

    # Always print to screen first
    print(output_text)

    # Then try clipboard unless disabled
    if not args.no_copy:
        ok, note = copy_to_clipboard(output_text)
        print(f"\n[Clipboard] {note}" if ok else f"\n[Clipboard] Skipped or failed: {note}")

if __name__ == "__main__":
    main()
