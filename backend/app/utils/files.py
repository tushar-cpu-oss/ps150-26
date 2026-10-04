"""Upload validation and safe file handling. No third-party imports."""
import os
import re
from pathlib import Path
from typing import BinaryIO, Optional

from app.utils.errors import AppError

ALLOWED_EXTENSIONS = {
    "mp4": {"video/mp4"},
    "avi": {"video/x-msvideo", "video/avi", "video/msvideo"},
    "mov": {"video/quicktime"},
    "mkv": {"video/x-matroska"},
    "dav": {"application/octet-stream", "video/x-dav"},
    "ifv": {"application/octet-stream", "video/x-ifv"},
    "h264": {"application/octet-stream", "video/h264"},
    "264": {"application/octet-stream", "video/h264"},
    "h265": {"application/octet-stream", "video/h265"},
    "hevc": {"application/octet-stream", "video/h265"},
    "dd": {"application/octet-stream"},
    "img": {"application/octet-stream"},
    "raw": {"application/octet-stream"},
    "e01": {"application/octet-stream"},
    "wav": {"audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave"},
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
    "png": {"image/png"},
}
VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "dav", "ifv", "h264", "264", "h265", "hevc", "ts", "mts", "m2ts", "webm"}
GENERIC_MIME = {"application/octet-stream", ""}
CHUNK_SIZE = 1024 * 1024


def sanitize_filename(name: Optional[str]) -> str:
    """Return a display-safe filename (basename only, restricted charset)."""
    name = (name or "").replace("\\", "/").split("/")[-1]
    name = name.replace("\x00", "")
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name).lstrip(".")
    return name[:120]


def get_extension(safe_name: str) -> str:
    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise AppError(
            415, "UNSUPPORTED_FILE_TYPE",
            f"File extension '.{ext}' is not supported. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}.",
        )
    return ext


def validate_declared_mime(ext: str, mime: Optional[str]) -> str:
    m = (mime or "").split(";")[0].strip().lower()
    if m in GENERIC_MIME:
        return m or "application/octet-stream"
    if m not in ALLOWED_EXTENSIONS[ext]:
        raise AppError(415, "MIME_TYPE_MISMATCH",
                       f"MIME type '{m}' does not match the '.{ext}' extension.")
    return m


def sniff_matches_extension(head: bytes, ext: str) -> bool:
    """Check magic bytes so a renamed file (e.g. an .exe named .mp4) is rejected."""
    if ext in ("mp4", "mov"):
        return len(head) >= 8 and head[4:8] in (b"ftyp", b"moov", b"mdat", b"free", b"wide")
    if ext == "avi":
        return head[:4] == b"RIFF" and head[8:12] == b"AVI "
    if ext == "wav":
        return head[:4] == b"RIFF" and head[8:12] == b"WAVE"
    if ext == "mkv":
        return head[:4] == b"\x1a\x45\xdf\xa3"
    if ext in ("dav", "ifv", "h264", "264", "h265", "hevc", "dd", "img", "raw", "e01"):
        return len(head) > 0
    if ext in ("jpg", "jpeg"):
        return head[:3] == b"\xff\xd8\xff"
    if ext == "png":
        return head[:8] == b"\x89PNG\r\n\x1a\n"
    return False


def safe_join(root: Path, *parts: str) -> Path:
    """Join and ensure the result stays inside root (path traversal protection)."""
    root_r = root.resolve()
    p = root_r.joinpath(*parts).resolve()
    if root_r != p and root_r not in p.parents:
        raise AppError(400, "INVALID_PATH", "Path escapes the storage directory.")
    return p


def copy_with_limit(src: BinaryIO, dest: Path, max_bytes: int, ext: str) -> int:
    """Stream src to dest in chunks; enforce size limit and magic-byte check.

    Returns bytes written. Removes the partial file on any failure.
    """
    written = 0
    first = True
    try:
        with open(dest, "wb") as out:
            while True:
                chunk = src.read(CHUNK_SIZE)
                if not chunk:
                    break
                if first:
                    if not sniff_matches_extension(chunk[:16], ext):
                        raise AppError(415, "CONTENT_MISMATCH",
                                       f"File content does not look like a valid '.{ext}' file.")
                    first = False
                written += len(chunk)
                if written > max_bytes:
                    raise AppError(413, "FILE_TOO_LARGE",
                                   f"File exceeds the maximum upload size of {max_bytes // (1024 * 1024)} MB.")
                out.write(chunk)
        if written == 0:
            raise AppError(400, "EMPTY_FILE", "Uploaded file is empty.")
    except BaseException:
        try:
            os.unlink(dest)
        except OSError:
            pass
        raise
    return written
