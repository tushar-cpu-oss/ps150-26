"""Baseline network acquisition using standard FFmpeg-supported stream protocols.

This is intentionally generic: it can acquire a standard RTSP/HTTP/HTTPS/RTMP stream
when the recorder exposes one. It does not claim OEM-private DVR protocol acquisition.
"""
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path
from urllib.parse import urlparse

from app.config import get_settings
from app.utils.errors import AppError

ALLOWED_SCHEMES = {"rtsp", "rtsps", "http", "https", "rtmp", "rtmps"}
SENSITIVE_URL = re.compile(r"(://[^:/@]+):([^@]+)@", re.IGNORECASE)


def redact_url(url: str) -> str:
    return SENSITIVE_URL.sub(r"\1:***@", url)


def validate_source_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in ALLOWED_SCHEMES or not parsed.netloc:
        raise AppError(422, "INVALID_STREAM_URL", "Use an RTSP/RTSPS/HTTP/HTTPS/RTMP/RTMPS stream URL.")
    if any(ch in url for ch in ("\n", "\r")):
        raise AppError(422, "INVALID_STREAM_URL", "Stream URL contains invalid control characters.")
    return url.strip()


def acquire_stream(url: str, output: Path, duration_seconds: int) -> dict:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AppError(503, "FFMPEG_UNAVAILABLE", "FFmpeg is required for standard network stream acquisition.")
    source = validate_source_url(url)
    duration = max(1, min(int(duration_seconds), 300))
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_name(output.name + ".part")
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", source,
           "-t", str(duration), "-map", "0:v:0?", "-an", "-c:v", "copy", str(tmp)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 45)
    except subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        raise AppError(504, "ACQUISITION_TIMEOUT", "Network stream acquisition timed out.")
    if proc.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        detail = (proc.stderr or "FFmpeg could not acquire the stream.")[-1200:]
        raise AppError(502, "ACQUISITION_FAILED", f"Standard stream acquisition failed: {detail}")
    os.replace(tmp, output)
    os.chmod(output, 0o440)
    return {"source_url": redact_url(source), "duration_seconds": duration,
            "stored_file": str(output), "size_bytes": output.stat().st_size,
            "method": "ffmpeg_standard_stream_capture"}
