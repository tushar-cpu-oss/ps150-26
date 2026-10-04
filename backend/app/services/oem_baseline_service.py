"""Conservative baseline inspection for DVR/NVR forensic images.

This layer does not pretend to reverse-engineer proprietary filesystems. It provides useful
first-pass fingerprinting and candidate-artifact discovery using evidence already available
in a raw/forensic image and The Sleuth Kit when installed.
"""
import re
import shutil
import subprocess
from pathlib import Path

VENDOR_MARKERS = {
    "Hikvision": [b"hikvision", b"hiksdk", b"hik"],
    "Dahua": [b"dahua", b"dhav"],
    "CP Plus": [b"cp plus", b"cpplus"],
    "Honeywell": [b"honeywell"],
    "TP-Link": [b"tp-link", b"tp_link", b"vigi"],
    "Godrej": [b"godrej"],
    "Uniview": [b"uniview", b"unv"],
    "Matrix": [b"matrix"],
}
CANDIDATE_EXTENSIONS = {
    ".dav", ".ifv", ".264", ".h264", ".h265", ".hevc", ".mp4", ".avi", ".mkv",
    ".db", ".idx", ".dat", ".rec", ".bin", ".log", ".ini", ".cfg"
}


def _run_fls(image: Path) -> list[str]:
    fls = shutil.which("fls")
    if not fls:
        return []
    p = subprocess.run([fls, "-r", "-p", str(image)], capture_output=True, text=True, timeout=180)
    if p.returncode != 0:
        return []
    return p.stdout.splitlines()


def baseline_inspect(image: Path, max_scan_mb: int = 32) -> dict:
    data = image.read_bytes()[: max_scan_mb * 1024 * 1024]
    lower = data.lower()
    hits = []
    for vendor, markers in VENDOR_MARKERS.items():
        matched = [m.decode("ascii", "ignore") for m in markers if m in lower]
        if matched:
            hits.append({"vendor": vendor, "markers": matched, "confidence": "low"})

    entries = _run_fls(image)
    candidates = []
    for line in entries:
        name = line.split(": ", 1)[-1].strip()
        if any(name.lower().endswith(ext) for ext in CANDIDATE_EXTENSIONS):
            deleted = "*" in line.split(": ", 1)[0]
            candidates.append({"entry": line[-500:], "deleted": deleted, "candidate_type": "media_or_recorder_artifact"})
            if len(candidates) >= 500:
                break

    return {
        "status": "BASELINE_INSPECTION_COMPLETED",
        "vendor_fingerprints": hits,
        "candidate_artifacts": candidates,
        "candidate_artifact_count": len(candidates),
        "scan_limit_mb": max_scan_mb,
        "sleuth_kit_file_listing": bool(shutil.which("fls")),
        "capabilities": {
            "vendor_fingerprint": "BASELINE_SIGNATURE_SCAN",
            "filesystem_reconstruction": "NOT_IMPLEMENTED",
            "proprietary_record_reconstruction": "NOT_IMPLEMENTED",
            "deleted_artifact_enumeration": "STANDARD_SLEUTH_KIT_WHERE_AVAILABLE",
            "direct_vendor_protocol": "NOT_IMPLEMENTED",
        },
        "limitations": [
            "Low-confidence byte-marker fingerprints are not proof of OEM identity.",
            "Candidate recorder artifacts are enumerated but proprietary indexes are not reconstructed.",
            "Vendor-private acquisition protocols are not inferred or fabricated.",
        ],
    }
