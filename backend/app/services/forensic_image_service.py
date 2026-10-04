"""Read-only forensic image ingestion and inspection.

Raw/DD/IMG images are hashed and, when The Sleuth Kit is installed, inspected without mounting
or modifying them. E01 is identified and hashed. Unsupported/proprietary filesystems are reported
rather than guessed.
"""
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from app.services.hashing_service import hash_file

IMAGE_EXTENSIONS = {"dd", "img", "raw", "e01", "001"}


@dataclass(frozen=True)
class ForensicImageArtifact:
    path: str
    image_type: Optional[str]
    size_bytes: int
    md5: str
    sha256: str
    parser_status: str


def detect_image_type(path: Path) -> str:
    with path.open("rb") as f:
        head = f.read(4096)
    if head.startswith(b"EVF") or head[0:8] == b"\x45\x56\x46\x09\x0d\x0a\xff\x00":
        return "EWF/E01"
    if len(head) >= 512 and head[510:512] == b"\x55\xaa":
        return "RAW/MBR-like"
    return "RAW/UNKNOWN"


def ingest_image_artifact(path: Path, image_type: Optional[str] = None) -> ForensicImageArtifact:
    p = Path(path)
    if not p.is_file(): raise FileNotFoundError(str(p))
    h = hash_file(p)
    return ForensicImageArtifact(path=str(p), image_type=image_type or detect_image_type(p),
                                 size_bytes=p.stat().st_size, md5=h["md5"], sha256=h["sha256"],
                                 parser_status="SLEUTH_KIT_AVAILABLE" if shutil.which("mmls") else "HASH_ONLY")


def _run(name: str, args: list[str], timeout: int = 120) -> dict:
    exe = shutil.which(name)
    if not exe: return {"available": False, "tool": name, "output": None}
    proc = subprocess.run([exe, *args], capture_output=True, text=True, timeout=timeout)
    return {"available": True, "tool": name, "returncode": proc.returncode,
            "output": (proc.stdout or proc.stderr)[-20000:]}


def inspect_image(path: Path) -> dict:
    artifact = ingest_image_artifact(path)
    partition_table = _run("mmls", [str(path)])
    filesystem = _run("fsstat", [str(path)])
    return {**asdict(artifact), "partition_table": partition_table, "filesystem": filesystem,
            "read_only": True,
            "limitations": [
                "Partition/filesystem inspection requires The Sleuth Kit in the runtime image.",
                "Unsupported proprietary DVR filesystems are reported rather than interpreted.",
                "Original image bytes are never modified by this service.",
            ]}


def find_deleted_standard_files(path: Path) -> list[dict]:
    """Use Sleuth Kit fls to enumerate deleted files when the filesystem is supported."""
    exe = shutil.which("fls")
    if not exe: return []
    proc = subprocess.run([exe, "-r", "-d", "-p", str(path)], capture_output=True, text=True, timeout=300)
    if proc.returncode != 0: return []
    out = []
    for line in proc.stdout.splitlines():
        if ": " not in line: continue
        inode, name = line.split(": ", 1)
        if not any(name.lower().endswith("." + ext) for ext in ("mp4", "avi", "mov", "mkv", "dav", "ifv", "264", "h264", "h265", "hevc")):
            continue
        out.append({"inode": inode.strip(), "name": name.strip()})
    return out
