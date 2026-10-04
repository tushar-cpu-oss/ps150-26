"""Preservation-safe decoding of CCTV containers to an analysis working copy."""
import shutil
import subprocess
from pathlib import Path

from app.utils.errors import AppError

SUPPORTED = {"dav", "ifv", "h264", "264", "h265", "hevc", "ts", "mts", "m2ts", "webm", "mp4", "mkv", "avi", "mov"}


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def decode_to_mp4(source: Path, destination: Path) -> Path:
    """Decode *source* into a separate MP4 working copy; source is never modified."""
    if source.suffix.lower().lstrip(".") not in SUPPORTED:
        raise AppError(415, "UNSUPPORTED_DECODER_INPUT", f"No decoder registered for {source.suffix}.")
    if not ffmpeg_available():
        raise AppError(503, "FFMPEG_NOT_FOUND", "FFmpeg is required for CCTV/raw stream decoding.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".part")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
           "-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast",
           "-c:a", "aac", "-movflags", "+faststart", str(tmp)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
        try: tmp.unlink()
        except OSError: pass
        raise AppError(422, "VIDEO_DECODE_ERROR", proc.stderr.strip()[-1000:] or "FFmpeg could not decode the evidence.")
    tmp.replace(destination)
    return destination
