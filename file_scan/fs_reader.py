# fs_reader.py
# OS-only helpers for fast file inventory plus media metadata via ffprobe.
# Windows-first but portable: Windows-specific bits are guarded.

from typing import Iterator, Tuple, Dict, Any, Optional, List
import string
import os
from pathlib import Path

# Master media set (lowercase, no dots). Extend as you like.
MEDIA_EXTENSIONS = {
    'mp3', 'mp4', 'wav', 'flac', 'mov', 'avi', 'mkv', 'webm', 'wmv',
    'm4a', 'aac', 'aiff', 'aif', 'ogg', 'opus', 'm4v', 'ts',
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'webp'
}

def get_size_on_disk(path: str) -> Optional[int]:
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        GetCompressedFileSizeW = ctypes.windll.kernel32.GetCompressedFileSizeW
        GetCompressedFileSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
        GetCompressedFileSizeW.restype = wintypes.DWORD
        high = wintypes.DWORD(0)
        low = GetCompressedFileSizeW(path, ctypes.byref(high))
        if low == 0xFFFFFFFF and ctypes.GetLastError() != 0:
            raise ctypes.WinError()
        return (high.value << 32) + low
    except Exception:
        return None

def iter_files(root_dir: str) -> Iterator[Tuple[str, os.DirEntry, os.stat_result]]:
    stack = [os.path.abspath(root_dir)]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                dirs = []
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            dirs.append(entry.path)
                            continue
                        if entry.is_file(follow_symlinks=False):
                            st = entry.stat(follow_symlinks=False)
                            yield (current, entry, st)
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
                stack.extend(reversed(dirs))
        except (PermissionError, FileNotFoundError, OSError):
            continue

def build_identity(dir_path: str, entry: os.DirEntry) -> Dict[str, str]:
    p = Path(dir_path) / entry.name
    name = p.stem
    extension = p.suffix.lower().lstrip(".")
    dir_norm = str(p.parent).replace("\\", "/")
    return {"dir_path": dir_norm, "name": name, "extension": extension}

def read_fast_stats(st: os.stat_result) -> Dict[str, int]:
    out: Dict[str, int] = {
        "size_bytes": int(st.st_size),
        "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))),
    }
    ctn = getattr(st, "st_ctime_ns", None)
    if ctn is not None:
        out["ctime_ns"] = int(ctn)
    return out

def read_windows_attrs(path: str) -> Dict[str, int]:
    """
    Return Windows-style attributes as 0/1 ints:
        - readonly
        - system

    We intentionally DO NOT return "hidden" or "archive" anymore, since those
    bits turned out not to be useful for this project.
    """
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            GetFileAttributesW = ctypes.windll.kernel32.GetFileAttributesW
            GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
            GetFileAttributesW.restype = wintypes.DWORD

            attrs = GetFileAttributesW(path)
            if attrs == 0xFFFFFFFF:
                # failed; fall back to "no special flags"
                return {"readonly": 0, "system": 0}

            FILE_ATTRIBUTE_READONLY = 0x0001
            FILE_ATTRIBUTE_SYSTEM   = 0x0004

            readonly = 1 if (attrs & FILE_ATTRIBUTE_READONLY) else 0
            system   = 1 if (attrs & FILE_ATTRIBUTE_SYSTEM)   else 0

            return {
                "readonly": readonly,
                "system":   system,
            }
        except Exception:
            return {"readonly": 0, "system": 0}

    # Non-Windows: no real concept of these attributes, just return zeros.
    return {"readonly": 0, "system": 0}

def get_media_metadata(path: str, extension: str) -> Dict[str, Any] | None:
    # Only attempt for known media types and if ffprobe is available.
    try:
        import shutil, subprocess, json
        if extension not in MEDIA_EXTENSIONS:
            return None
        if not shutil.which("ffprobe"):
            return None
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            encoding="utf-8", timeout=10
        )
        if result.returncode != 0:
            return None
        md = json.loads(result.stdout)
        data: Dict[str, Any] = {
            "duration": None,
            "bitrate": None,
            "codec": None,
            "framerate": None,
            "image_format": None,
            "resolution_width": None,
            "resolution_height": None,
            "sample_rate": None,
            "channels": None,
            # tag fields:
            "tag_title": None,
            "tag_artist": None,
            "tag_album": None,
            "tag_album_artist": None,
            "tag_track": None,
            "tag_date": None,
        }
        fmt = md.get("format", {})
        try:
            if "duration" in fmt:
                data["duration"] = float(fmt["duration"])
        except Exception:
            pass
        try:
            if "bit_rate" in fmt:
                data["bitrate"] = int(fmt["bit_rate"])
        except Exception:
            pass
        if "format_name" in fmt:
            data["image_format"] = fmt["format_name"]
        for stream in md.get("streams", []):
            ctype = stream.get("codec_type")
            if data["codec"] is None and stream.get("codec_name"):
                data["codec"] = stream["codec_name"]
            if ctype == "video":
                if stream.get("width"):
                    data["resolution_width"] = stream["width"]
                if stream.get("height"):
                    data["resolution_height"] = stream["height"]
                r = stream.get("r_frame_rate")
                if r and r != "0/0":
                    try:
                        num, den = r.split("/")
                        den_f = float(den)
                        data["framerate"] = float(num) / den_f if den_f else None
                    except Exception:
                        pass
            elif ctype == "audio":
                try:
                    if stream.get("sample_rate"):
                        data["sample_rate"] = int(stream["sample_rate"])
                except Exception:
                    pass
                try:
                    if stream.get("channels"):
                        data["channels"] = int(stream["channels"])
                except Exception:
                    pass
        return data
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None

def collect_full_record(dir_path: str, entry: os.DirEntry, st: os.stat_result) -> Dict[str, Any]:
    ident = build_identity(dir_path, entry)
    stats = read_fast_stats(st)
    path = os.path.join(dir_path, entry.name)
    attrs = read_windows_attrs(path)
    rec: Dict[str, Any] = {}
    rec.update(ident)
    rec.update(stats)
    rec.update(attrs)
    sod = get_size_on_disk(path)
    if sod is not None:
        rec["size_on_disk"] = int(sod)
    try:
        rec["is_symlink"] = 1 if entry.is_symlink() else 0
    except Exception:
        rec["is_symlink"] = 0
    # Media metadata (best-effort)
    media = get_media_metadata(path, ident["extension"])
    if media:
        rec.update(media)
    return rec

def compute_fast_fingerprint(size_bytes: int, mtime_ns: int) -> str:
    return f"{size_bytes}:{mtime_ns}"

def directory_fingerprint(dir_path: str) -> str:
    count = 0
    max_mtime = 0
    try:
        with os.scandir(dir_path) as it:
            for entry in it:
                try:
                    st = entry.stat(follow_symlinks=False)
                    count += 1
                    mt = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)))
                    if mt > max_mtime:
                        max_mtime = mt
                except Exception:
                    continue
    except Exception:
        pass
    return f"{count}:{max_mtime}"

def iter_full_records(root_dir: str):
    for dir_path, entry, st in iter_files(root_dir):
        yield collect_full_record(dir_path, entry, st)

def _extract_ffprobe_tags(md: Dict[str, Any]) -> Dict[str, Any]:
    """
    Best-effort extraction of common media tags from ffprobe JSON.
    Returns keys:
        tag_title, tag_artist, tag_album, tag_album_artist,
        tag_track, tag_date
    All values may be None.
    """
    tags_lower: Dict[str, str] = {}

    def merge_tag_dict(src: Optional[Dict[str, Any]]) -> None:
        if not src:
            return
        for k, v in src.items():
            if v is None:
                continue
            lk = k.lower()
            if lk not in tags_lower:
                tags_lower[lk] = str(v)

    fmt = md.get("format", {})
    merge_tag_dict(fmt.get("tags"))

    for stream in md.get("streams", []):
        merge_tag_dict(stream.get("tags"))

    out: Dict[str, Any] = {
        "tag_title":        None,
        "tag_artist":       None,
        "tag_album":        None,
        "tag_album_artist": None,
        "tag_track":        None,
        "tag_date":         None,
    }

    out["tag_title"]        = tags_lower.get("title")
    out["tag_artist"]       = tags_lower.get("artist")
    out["tag_album"]        = tags_lower.get("album")
    out["tag_album_artist"] = (
        tags_lower.get("album_artist")
        or tags_lower.get("albumartist")
        or tags_lower.get("album artist")
    )
    out["tag_track"]        = (
        tags_lower.get("track")
        or tags_lower.get("tracknumber")
        or tags_lower.get("track number")
    )
    out["tag_date"]         = (
        tags_lower.get("date")
        or tags_lower.get("year")
        or tags_lower.get("original date")
    )

    return out


def _windows_get_volume_info(root_path: str) -> Optional[Dict[str, Any]]:
    """
    Low-level helper: get basic volume info for a given root path on Windows.
    """
    if os.name != "nt":
        return None

    try:
        import ctypes
        from ctypes import wintypes

        root_path = os.path.abspath(root_path)
        drive, _ = os.path.splitdrive(root_path)
        if not drive:
            return None
        root = drive.upper() + "\\"

        GetVolumeInformationW = ctypes.windll.kernel32.GetVolumeInformationW
        GetVolumeInformationW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPWSTR,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPWSTR,
            wintypes.DWORD,
        ]
        GetVolumeInformationW.restype = wintypes.BOOL

        volume_name_buf = ctypes.create_unicode_buffer(256)
        fs_name_buf = ctypes.create_unicode_buffer(256)
        serial_number = wintypes.DWORD()
        max_component_length = wintypes.DWORD()
        fs_flags = wintypes.DWORD()

        ok = GetVolumeInformationW(
            root,
            volume_name_buf,
            len(volume_name_buf),
            ctypes.byref(serial_number),
            ctypes.byref(max_component_length),
            ctypes.byref(fs_flags),
            fs_name_buf,
            len(fs_name_buf),
        )
        if not ok:
            return None

        label = volume_name_buf.value or None
        filesystem = fs_name_buf.value or None
        serial_hex = f"{serial_number.value:08X}"

        if filesystem:
            volume_key = f"{serial_hex}-{filesystem}"
        else:
            volume_key = serial_hex

        return {
            "root_path": root,
            "label": label,
            "filesystem": filesystem,
            "serial_number": serial_hex,
            "volume_key": volume_key,
        }
    except Exception:
        return None

def get_volume_info(root_path: str) -> Dict[str, Any]:
    """
    Public API: get volume information for a given path or drive.
    """
    if os.name == "nt":
        info = _windows_get_volume_info(root_path)
        if info is not None:
            return info

    rp = os.path.abspath(root_path)
    return {
        "root_path": rp,
        "label": None,
        "filesystem": None,
        "serial_number": None,
        "volume_key": rp.replace("\\", "/"),
    }

def get_volume_info_for_drive(drive_letter: str) -> Dict[str, Any]:
    drive_letter = drive_letter.upper()
    root = f"{drive_letter}:\\"
    return get_volume_info(root)

def list_available_drive_roots() -> List[str]:
    if os.name != "nt":
        return ["/"]
    roots: List[str] = []
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if os.path.exists(root):
            roots.append(root)
    return roots

def list_available_drive_letters() -> List[str]:
    if os.name != "nt":
        return []
    return [root[0] for root in list_available_drive_roots()]

def iter_dirs(root_dir: str) -> Iterator[str]:
    """
    Recursively yield all directories starting at root_dir.
    Includes the root_dir itself.
    """
    stack = [os.path.abspath(root_dir)]
    while stack:
        current = stack.pop()
        yield current
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
        except (PermissionError, FileNotFoundError, OSError):
            continue

def iter_files_in_directory(dir_path: str) -> Iterator[Tuple[os.DirEntry, os.stat_result]]:
    """
    Yield all *files directly in this directory* (non-recursive).
    """
    try:
        with os.scandir(dir_path) as it:
            for entry in it:
                try:
                    if entry.is_file(follow_symlinks=False):
                        st = entry.stat(follow_symlinks=False)
                        yield entry, st
                except (PermissionError, FileNotFoundError, OSError):
                    continue
    except (PermissionError, FileNotFoundError, OSError):
        return