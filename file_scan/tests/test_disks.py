# test_disks.py
#
# Quick test for the fs_reader volume helpers.
# - Lists available drives / roots
# - Prints volume info for each

from pprint import pprint
import os

from file_scan import fs_reader


def main() -> None:
    print("OS name:", os.name)
    print()

    # 1) List available roots / drives
    roots = fs_reader.list_available_drive_roots()
    print("Available roots:")
    for r in roots:
        print("  ", r)
    print()

    # 2) On Windows, also show drive letters
    if os.name == "nt":
        letters = fs_reader.list_available_drive_letters()
        print("Available drive letters:")
        print("  ", ", ".join(letters))
        print()

    # 3) Get volume info for each root
    print("Volume info:")
    for root in roots:
        info = fs_reader.get_volume_info(root)
        print(f"Root: {root}")
        pprint(info)
        print("-" * 40)


if __name__ == "__main__":
    main()
