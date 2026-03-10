# app/utils/clipboard.py
"""
Clipboard utilities for printing and copying text simultaneously.

This module provides print_copy(), which prints text to stdout and also
copies it to the system clipboard for use with screen readers or other
accessibility tools.
"""
import subprocess
import sys


def copy_to_clipboard(text: str) -> bool:
    """
    Copy text to the system clipboard.

    Returns True if successful, False otherwise.
    Works on Windows, macOS, and Linux (with xclip installed).
    """
    text = str(text)

    try:
        if sys.platform == "win32":
            # Windows: use clip.exe
            process = subprocess.Popen(
                ["clip"],
                stdin=subprocess.PIPE,
                shell=True
            )
            process.communicate(input=text.encode("utf-16le"))
            return process.returncode == 0

        elif sys.platform == "darwin":
            # macOS: use pbcopy
            process = subprocess.Popen(
                ["pbcopy"],
                stdin=subprocess.PIPE
            )
            process.communicate(input=text.encode("utf-8"))
            return process.returncode == 0

        else:
            # Linux: try xclip
            process = subprocess.Popen(
                ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE
            )
            process.communicate(input=text.encode("utf-8"))
            return process.returncode == 0

    except Exception:
        return False


def print_copy(text: str, end: str = "\n") -> None:
    """
    Print text to stdout AND copy it to the clipboard.

    This is useful for accessibility - a speech synthesizer monitoring
    the clipboard can narrate the most important program outputs.

    Args:
        text: The text to print and copy
        end: String appended after the text (default: newline)

    Usage:
        print_copy("Query completed: 15 files found")
        print_copy("Moving file.txt to /archive/")
    """
    full_text = text + end
    print(text, end=end)
    copy_to_clipboard(full_text.rstrip("\n"))  # Don't include trailing newline in clipboard
