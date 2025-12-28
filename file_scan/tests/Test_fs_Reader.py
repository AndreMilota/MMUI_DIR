# Test_sf_Reader.py
# Default root is ~/Downloads so you can just run it in PyCharm.

from __future__ import annotations
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
from file_scan import fs_reader


def pick_first_n_files(root: str, n: int) -> List[Dict[str, Any]]:
    picked: List[Dict[str, Any]] = []
    for rec in fs_reader.iter_full_records(root):
        picked.append(rec)
        if len(picked) >= n:
            break
    return picked


def find_any_mp3(root: str) -> Dict[str, Any] | None:
    for rec in fs_reader.iter_full_records(root):
        if rec.get("extension") == "mp3":
            return rec
    return None


def first_subfolder_with_files(root: str) -> str | None:
    queue = [os.path.abspath(root)]
    seen = set()
    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        try:
            has_file = False
            subdirs = []
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            has_file = True
                        elif entry.is_dir(follow_symlinks=False):
                            subdirs.append(entry.path)
                    except Exception:
                        continue
            if has_file and current != os.path.abspath(root):
                return current
            queue.extend(subdirs)
        except Exception:
            continue
    return None


def print_record(label: str, rec: Dict[str, Any]) -> None:
    path = f'{rec.get("dir_path", "")}/{rec.get("name", "")}'
    ext = rec.get("extension", "")
    print(f"\n{label}")
    print(f"  file: {path}.{ext}" if ext else f"  file: {path}")
    print(f"  size_bytes: {rec.get('size_bytes', 0)}")
    print(f"  mtime_ns:   {rec.get('mtime_ns', 0)}")
    print(
        "  attrs: "
        f"readonly={rec.get('readonly', 0)} "
        f"hidden={rec.get('hidden', 0)} "
        f"system={rec.get('system', 0)} "
        f"archive={rec.get('archive', 0)} "
        f"symlink={rec.get('is_symlink', 0)}"
    )
    if rec.get("size_on_disk") is not None:
        print(f"  size_on_disk: {rec.get('size_on_disk')}")

    # Media details (print only if present)
    media_fields = [
        ("codec", "codec"),
        ("bitrate", "bitrate"),
        ("duration", "duration"),
        ("sample_rate", "sample_rate"),
        ("channels", "channels"),
        ("framerate", "framerate"),
        ("image_format", "image_format"),
        ("resolution_width", "resolution_width"),
        ("resolution_height", "resolution_height"),
    ]
    present = [name for name, key in media_fields if rec.get(key) not in (None, "", 0)]
    if present:
        print("  media:")
        for label2, key in media_fields:
            val = rec.get(key)
            if val not in (None, "", 0):
                print(f"    {label2}: {val}")


Key = Tuple[str, str, str]  # (dir_path, name, extension)


def scan_fingerprints(root: str) -> Dict[Key, str]:
    out: Dict[Key, str] = {}
    for rec in fs_reader.iter_full_records(root):
        key: Key = (rec["dir_path"], rec["name"], rec.get("extension", ""))
        fp = fs_reader.compute_fast_fingerprint(rec["size_bytes"], rec["mtime_ns"])
        out[key] = fp
    return out


def demo_modify_detection(root: str) -> None:
    """
    Optional demo: create a junk file in the project directory,
    modify it, and show that the fingerprint changes.

    This is just a sanity demo and not required for normal use.
    """
    # Put the junk file next to this script, not in Downloads.
    script_dir = Path(__file__).resolve().parent
    junk = script_dir / "junk_sanity.txt"

    try:
        junk.write_text("first version\n", encoding="utf-8")
    except Exception as e:
        print(f"\n[INFO] Skipping modify-detection demo; could not write {junk}: {e}")
        return

    f1 = scan_fingerprints(root)
    key = (str(junk.parent).replace("\\", "/"), junk.stem, junk.suffix.lstrip("."))

    print("\n=== Modify-detection demo: first scan ===")
    if key in f1:
        print(f"  Found {junk.name} fingerprint: {f1[key]}")
    else:
        print(f"  Did not locate {junk.name} in first scan (not in DB / not under this root).")

    time.sleep(1.1)

    try:
        with junk.open("a", encoding="utf-8") as fh:
            fh.write("second version (appended)\n")
    except Exception as e:
        print(f"[INFO] Skipping second part of modify-detection demo; could not modify {junk}: {e}")
        return

    f2 = scan_fingerprints(root)
    print("=== Modify-detection demo: second scan ===")
    if key in f2:
        print(f"  New {junk.name} fingerprint: {f2[key]}")
        if key in f1 and f2[key] != f1[key]:
            print("  RESULT: Change detected ✔ (size or mtime_ns differs)")
        else:
            print("  RESULT: No change detected ✘ (fingerprint identical)")
    else:
        print(f"  {junk.name} not found in second scan (not in DB / not under this root).")


def main() -> None:
    default_root = os.path.join(os.path.expanduser("~"), "Downloads")
    root = sys.argv[1] if len(sys.argv) >= 2 else default_root
    if not Path(root).exists() or not Path(root).is_dir():
        print(f"Error: '{root}' is not a directory.")
        sys.exit(2)

    print(f"Root: {root}")

    first_set = pick_first_n_files(root, 5)
    mp3_rec = find_any_mp3(root)
    if mp3_rec is not None and not any(r.get("extension") == "mp3" for r in first_set):
        if len(first_set) >= 5:
            first_set[-1] = mp3_rec
        else:
            first_set.append(mp3_rec)

    print("\n=== Sample from root (up to 5 files, preferring an MP3) ===")
    for i, rec in enumerate(first_set, 1):
        print_record(f"[root {i}]", rec)

    sub = first_subfolder_with_files(root)
    if sub:
        second_set = pick_first_n_files(sub, 5)
        print(f"\n=== Sample from first subfolder with files ===\nSubfolder: {sub}")
        for i, rec in enumerate(second_set, 1):
            print_record(f"[sub {i}]", rec)
    else:
        print("\nNo subfolder with files was found.")

    # Optional: you can comment this out entirely if you don't care about the demo.
    demo_modify_detection(root)


if __name__ == "__main__":
    main()
