"""Real metadata extraction via FFprobe, with an OpenCV fallback for frame data."""
import json
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.utils.timeutil import to_naive_utc

log = logging.getLogger(__name__)


def ffprobe_available() -> bool:
    return shutil.which("ffprobe") is not None


def _fraction(s: Optional[str]) -> Optional[float]:
    if not s or s in ("0/0", "N/A"):
        return None
    try:
        if "/" in s:
            n, d = s.split("/")
            return float(n) / float(d) if float(d) else None
        return float(s)
    except ValueError:
        return None


def _float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int(v: Any) -> Optional[int]:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def run_ffprobe(path: Path) -> Dict[str, Any]:
    if not ffprobe_available():
        raise RuntimeError("FFPROBE_NOT_FOUND: ffprobe is not installed or not on PATH. Install FFmpeg (apt install ffmpeg).")
    cmd = ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)  # argv list: no shell
    if proc.returncode != 0:
        raise RuntimeError(f"VIDEO_DECODE_ERROR: ffprobe failed: {proc.stderr.strip()[:300]}")
    return json.loads(proc.stdout)


def _opencv_frame_count(path: Path) -> Optional[int]:
    try:
        import cv2

        cap = cv2.VideoCapture(str(path))
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        return n if n > 0 else None
    except Exception:  # pragma: no cover
        return None


def parse_creation_time(tags: Dict[str, Any]) -> Optional[datetime]:
    for key in ("creation_time", "com.apple.quicktime.creationdate", "date"):
        raw = tags.get(key)
        if not raw:
            continue
        try:
            dt = to_naive_utc(datetime.fromisoformat(str(raw).replace("Z", "+00:00")))
            if dt.year >= 2000:  # ignore epoch/zeroed timestamps written by some encoders
                return dt
        except ValueError:
            continue
    return None


def extract_metadata(path: Path, original_filename: str) -> Dict[str, Any]:
    """Extract actual container/stream metadata. Missing values are None, never invented."""
    probe = run_ffprobe(path)
    fmt = probe.get("format", {}) or {}
    streams = probe.get("streams", []) or []
    video = [s for s in streams if s.get("codec_type") == "video"]
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    v = video[0] if video else {}

    fps = _fraction(v.get("avg_frame_rate")) or _fraction(v.get("r_frame_rate"))
    duration = _float(fmt.get("duration")) or _float(v.get("duration"))
    frame_count = _int(v.get("nb_frames"))
    frame_count_source = "ffprobe_nb_frames"
    if frame_count is None and video:
        frame_count = _opencv_frame_count(path)
        frame_count_source = "opencv_cap_prop"
        if frame_count is None and duration and fps:
            frame_count = int(round(duration * fps))
            frame_count_source = "estimated_duration_x_fps"
    if frame_count is None:
        frame_count_source = None

    tags = {**(fmt.get("tags") or {})}
    return {
        "filename": original_filename,
        "format": fmt.get("format_name"),
        "format_long_name": fmt.get("format_long_name"),
        "duration": duration,
        "bit_rate": _int(fmt.get("bit_rate")),
        "width": _int(v.get("width")),
        "height": _int(v.get("height")),
        "fps": fps,
        "frame_count": frame_count,
        "frame_count_source": frame_count_source,
        "codec": v.get("codec_name") or (audio[0].get("codec_name") if audio else None),
        "video_streams": len(video),
        "audio_streams": len(audio),
        "streams": [
            {
                "index": s.get("index"),
                "codec_type": s.get("codec_type"),
                "codec_name": s.get("codec_name"),
                "sample_rate": _int(s.get("sample_rate")),
                "channels": s.get("channels"),
            }
            for s in streams
        ],
        "creation_time": parse_creation_time(tags),
        "tags": {str(k): str(x) for k, x in tags.items()},
        "stream_tags": [
            {str(k): str(x) for k, x in (s.get("tags") or {}).items()} for s in streams
        ],
        "extracted_with": "ffprobe",
    }
