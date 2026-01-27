"""
test_db_comparison.py

Compare old_file_database.sqlite with file_database.sqlite to verify
that the refactored fs_reader/fs_load produces equivalent results.

Expected differences:
- Timestamps in the database metadata (scan times)
- Potentially minor differences in directory fingerprints if files changed

Things that should be identical:
- Number of volumes, directories, and files
- File names, extensions, sizes
- Volume information
"""

import os
import sqlite3
from pathlib import Path

# Path to the databases
SCRIPT_DIR = Path(__file__).resolve().parent.parent
OLD_DB_PATH = SCRIPT_DIR / "old_file_database.sqlite"
NEW_DB_PATH = SCRIPT_DIR / "file_database.sqlite"


def get_db_connection(db_path: Path) -> sqlite3.Connection:
    """Open a database connection with row factory."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def compare_file_sizes():
    """Compare the file sizes of the two databases."""
    old_size = OLD_DB_PATH.stat().st_size
    new_size = NEW_DB_PATH.stat().st_size

    print(f"\n{'='*60}")
    print("FILE SIZE COMPARISON")
    print(f"{'='*60}")
    print(f"Old database: {old_size:,} bytes")
    print(f"New database: {new_size:,} bytes")
    print(f"Difference:   {new_size - old_size:,} bytes ({(new_size - old_size) / old_size * 100:.2f}%)")

    return old_size, new_size


def compare_row_counts():
    """Compare row counts in each table."""
    old_conn = get_db_connection(OLD_DB_PATH)
    new_conn = get_db_connection(NEW_DB_PATH)

    tables = ['volumes', 'directories', 'files']

    print(f"\n{'='*60}")
    print("ROW COUNT COMPARISON")
    print(f"{'='*60}")
    print(f"{'Table':<15} {'Old DB':>12} {'New DB':>12} {'Diff':>10}")
    print(f"{'-'*15} {'-'*12} {'-'*12} {'-'*10}")

    counts = {}
    all_match = True

    for table in tables:
        old_count = old_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        new_count = new_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        diff = new_count - old_count
        counts[table] = (old_count, new_count, diff)

        diff_str = f"{diff:+d}" if diff != 0 else "0"
        print(f"{table:<15} {old_count:>12,} {new_count:>12,} {diff_str:>10}")

        if diff != 0:
            all_match = False

    old_conn.close()
    new_conn.close()

    return counts, all_match


def compare_volumes():
    """Compare volume records."""
    old_conn = get_db_connection(OLD_DB_PATH)
    new_conn = get_db_connection(NEW_DB_PATH)

    print(f"\n{'='*60}")
    print("VOLUME COMPARISON")
    print(f"{'='*60}")

    old_volumes = {row['volume_key']: dict(row) for row in
                   old_conn.execute("SELECT * FROM volumes")}
    new_volumes = {row['volume_key']: dict(row) for row in
                   new_conn.execute("SELECT * FROM volumes")}

    # Check for matching volume keys
    old_keys = set(old_volumes.keys())
    new_keys = set(new_volumes.keys())

    if old_keys == new_keys:
        print(f"Volume keys match: {len(old_keys)} volume(s)")
    else:
        print(f"Volume key mismatch!")
        print(f"  Only in old: {old_keys - new_keys}")
        print(f"  Only in new: {new_keys - old_keys}")

    # Compare volume attributes (excluding timestamps)
    for key in old_keys & new_keys:
        old_vol = old_volumes[key]
        new_vol = new_volumes[key]

        compare_fields = ['root_path', 'label', 'filesystem', 'serial_number']
        for field in compare_fields:
            if old_vol.get(field) != new_vol.get(field):
                print(f"  {key}: {field} differs: {old_vol.get(field)!r} vs {new_vol.get(field)!r}")

    old_conn.close()
    new_conn.close()

    return old_keys == new_keys


def compare_directories():
    """Compare directory records."""
    old_conn = get_db_connection(OLD_DB_PATH)
    new_conn = get_db_connection(NEW_DB_PATH)

    print(f"\n{'='*60}")
    print("DIRECTORY COMPARISON")
    print(f"{'='*60}")

    # Get directories by path (joining with volumes for full identification)
    old_dirs = {}
    for row in old_conn.execute("""
        SELECT d.*, v.volume_key
        FROM directories d
        JOIN volumes v ON d.volume_id = v.id
    """):
        key = (row['volume_key'], row['dir_path'])
        old_dirs[key] = dict(row)

    new_dirs = {}
    for row in new_conn.execute("""
        SELECT d.*, v.volume_key
        FROM directories d
        JOIN volumes v ON d.volume_id = v.id
    """):
        key = (row['volume_key'], row['dir_path'])
        new_dirs[key] = dict(row)

    old_keys = set(old_dirs.keys())
    new_keys = set(new_dirs.keys())

    only_in_old = old_keys - new_keys
    only_in_new = new_keys - old_keys
    common = old_keys & new_keys

    print(f"Directories in both: {len(common)}")
    print(f"Only in old DB:      {len(only_in_old)}")
    print(f"Only in new DB:      {len(only_in_new)}")

    if only_in_old:
        print("\nDirectories only in old database:")
        for key in sorted(only_in_old)[:10]:  # Show first 10
            print(f"  {key[1]}")
        if len(only_in_old) > 10:
            print(f"  ... and {len(only_in_old) - 10} more")

    if only_in_new:
        print("\nDirectories only in new database:")
        for key in sorted(only_in_new)[:10]:
            print(f"  {key[1]}")
        if len(only_in_new) > 10:
            print(f"  ... and {len(only_in_new) - 10} more")

    old_conn.close()
    new_conn.close()

    return len(only_in_old) == 0 and len(only_in_new) == 0


def compare_files():
    """Compare file records."""
    old_conn = get_db_connection(OLD_DB_PATH)
    new_conn = get_db_connection(NEW_DB_PATH)

    print(f"\n{'='*60}")
    print("FILE COMPARISON")
    print(f"{'='*60}")

    # Get files by (volume_key, dir_path, name, extension)
    def get_files(conn):
        files = {}
        for row in conn.execute("""
            SELECT f.*, d.dir_path, v.volume_key
            FROM files f
            JOIN directories d ON f.directory_id = d.id
            JOIN volumes v ON d.volume_id = v.id
        """):
            key = (row['volume_key'], row['dir_path'], row['name'], row['extension'])
            files[key] = dict(row)
        return files

    old_files = get_files(old_conn)
    new_files = get_files(new_conn)

    old_keys = set(old_files.keys())
    new_keys = set(new_files.keys())

    only_in_old = old_keys - new_keys
    only_in_new = new_keys - old_keys
    common = old_keys & new_keys

    print(f"Files in both:   {len(common)}")
    print(f"Only in old DB:  {len(only_in_old)}")
    print(f"Only in new DB:  {len(only_in_new)}")

    if only_in_old:
        print("\nFiles only in old database:")
        for key in sorted(only_in_old)[:10]:
            filename = f"{key[2]}.{key[3]}" if key[3] else key[2]
            print(f"  {key[1]}/{filename}")
        if len(only_in_old) > 10:
            print(f"  ... and {len(only_in_old) - 10} more")

    if only_in_new:
        print("\nFiles only in new database:")
        for key in sorted(only_in_new)[:10]:
            filename = f"{key[2]}.{key[3]}" if key[3] else key[2]
            print(f"  {key[1]}/{filename}")
        if len(only_in_new) > 10:
            print(f"  ... and {len(only_in_new) - 10} more")

    # For common files, compare key attributes (not timestamps)
    mismatches = []
    compare_fields = [
        'size_bytes', 'size_on_disk', 'readonly', 'system', 'is_symlink',
        'duration', 'bitrate', 'codec', 'framerate', 'image_format',
        'resolution_width', 'resolution_height', 'sample_rate', 'channels',
        'tag_title', 'tag_artist', 'tag_album', 'tag_album_artist',
        'tag_track', 'tag_date'
    ]

    for key in common:
        old_file = old_files[key]
        new_file = new_files[key]

        for field in compare_fields:
            old_val = old_file.get(field)
            new_val = new_file.get(field)
            if old_val != new_val:
                mismatches.append((key, field, old_val, new_val))

    if mismatches:
        print(f"\nAttribute mismatches in common files: {len(mismatches)}")
        for key, field, old_val, new_val in mismatches[:10]:
            filename = f"{key[2]}.{key[3]}" if key[3] else key[2]
            print(f"  {filename}: {field} = {old_val!r} -> {new_val!r}")
        if len(mismatches) > 10:
            print(f"  ... and {len(mismatches) - 10} more")
    else:
        print(f"\nAll {len(common)} common files have matching attributes!")

    old_conn.close()
    new_conn.close()

    return len(only_in_old) == 0 and len(only_in_new) == 0 and len(mismatches) == 0


def main():
    """Run all comparisons."""
    print("\n" + "="*60)
    print("DATABASE COMPARISON: old_file_database.sqlite vs file_database.sqlite")
    print("="*60)

    # Check that both files exist
    if not OLD_DB_PATH.exists():
        print(f"ERROR: Old database not found: {OLD_DB_PATH}")
        return False

    if not NEW_DB_PATH.exists():
        print(f"ERROR: New database not found: {NEW_DB_PATH}")
        return False

    # Run comparisons
    compare_file_sizes()
    counts, counts_match = compare_row_counts()
    volumes_match = compare_volumes()
    dirs_match = compare_directories()
    files_match = compare_files()

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    all_pass = counts_match and volumes_match and dirs_match and files_match

    print(f"Row counts match:    {'PASS' if counts_match else 'FAIL'}")
    print(f"Volumes match:       {'PASS' if volumes_match else 'FAIL'}")
    print(f"Directories match:   {'PASS' if dirs_match else 'FAIL'}")
    print(f"Files match:         {'PASS' if files_match else 'FAIL'}")
    print(f"\nOverall result:      {'PASS' if all_pass else 'FAIL'}")

    return all_pass


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
