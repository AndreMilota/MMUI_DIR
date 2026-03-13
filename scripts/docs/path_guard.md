# PathGuard - File Access Control

The `PathGuard` class manages file/directory access permissions using a **whitelist-first** approach. By default, all paths are blocked. You must explicitly allow access.

## Location

```
app_2/path_guard.py
```

## Design Philosophy

**Default closed**: Nothing is accessible until explicitly allowed. This prevents accidentally exposing files if you forget to configure rules.

**Rule layering**:
1. `allow()` - opens up paths for access
2. `deny()` - blocks portions of allowed paths
3. `allow()` - can re-open portions of denied paths

Rules are evaluated in order. The last matching rule wins.

## Basic Usage

```python
from file_scan.path_guard import PathGuard

pg = PathGuard()

# Nothing is allowed by default
pg.ok("DISK001", "any/path")  # False

# Allow a directory
pg.allow("DISK001", "photos")
pg.ok("DISK001", "photos/pic.jpg")  # True
pg.ok("DISK001", "documents/file.txt")  # False (not allowed)

# Deny a subdirectory within allowed area
pg.deny("DISK001", "photos/private")
pg.ok("DISK001", "photos/public/pic.jpg")  # True
pg.ok("DISK001", "photos/private/secret.jpg")  # False

# Re-allow within denied area
pg.allow("DISK001", "photos/private/shared")
pg.ok("DISK001", "photos/private/shared/pic.jpg")  # True
```

## Path Patterns

Paths are specified using a disk ID (e.g., serial number) and a path pattern.

### Path Separators
Both forward slashes (`/`) and backslashes (`\`) are accepted and normalized internally.

```python
pg.allow("DISK001", "photos\\vacation")  # Same as "photos/vacation"
```

### Wildcards

| Pattern | Description | Example |
|---------|-------------|---------|
| `*` | Matches any characters within a single path segment | `music/*.mp3` matches `music/song.mp3` but not `music/rock/song.mp3` |
| `**` | Matches zero or more complete path segments (recursive) | `music/**/*.mp3` matches `music/song.mp3` and `music/rock/classic/song.mp3` |
| `?` | Matches any single character | `file?.txt` matches `file1.txt` but not `file12.txt` |

### Pattern Examples

```python
# Allow all TXT files directly in docs folder
pg.allow("DISK001", "docs/*.txt")

# Allow all MP3 files anywhere under music (recursive)
pg.allow("DISK001", "music/**/*.mp3")

# Allow a specific file only
pg.allow("DISK001", "config/settings.json")

# Allow entire directory and all subdirectories
pg.allow("DISK001", "documents")
```

## API Reference

### `allow(disk_id: str, path: str) -> None`

Allows access to a path pattern. Call this to open up paths for access.

**Parameters:**
- `disk_id`: Identifier for the disk (e.g., serial number)
- `path`: Path pattern to allow

### `deny(disk_id: str, path: str) -> None`

Denies access to a path pattern. Use this to block portions of previously allowed paths.

**Parameters:**
- `disk_id`: Identifier for the disk
- `path`: Path pattern to block

### `ok(disk_id: str, path: str) -> bool`

Checks if access to a path is allowed.

**Parameters:**
- `disk_id`: Identifier for the disk
- `path`: Path to check

**Returns:**
- `True`: Access is allowed (matched by an allow rule, not overridden by deny)
- `False`: Access is blocked (no matching allow, or denied)

**Conservative behavior:** If the path contains wildcards and could potentially match denied content, returns `False`.

## Disk IDs

Disk IDs are arbitrary strings that identify a storage device. Rules are disk-specific:

```python
pg.allow("DISK001", "data")
pg.ok("DISK001", "data/file.txt")  # True
pg.ok("DISK002", "data/file.txt")  # False (different disk, not allowed)
```

## Rule Evaluation

1. Rules are evaluated in the order they were added
2. The **last matching rule** determines access
3. If no rules match, access is **denied** (default closed)

```python
pg.allow("DISK001", "data")           # Rule 1: allow
pg.deny("DISK001", "data/secret")     # Rule 2: deny
pg.allow("DISK001", "data/secret/ok") # Rule 3: allow

pg.ok("DISK001", "data/file.txt")          # True (Rule 1)
pg.ok("DISK001", "data/secret/file.txt")   # False (Rule 2)
pg.ok("DISK001", "data/secret/ok/file.txt") # True (Rule 3)
```

## Tests

Run the test suite:

```bash
python -m scripts.path_guard_tests
```
