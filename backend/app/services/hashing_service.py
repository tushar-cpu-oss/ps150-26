"""Cryptographic hashing. Hashes are always computed from real file bytes, in chunks."""
import hashlib
from pathlib import Path
from typing import Dict

from app.utils.timeutil import utcnow

CHUNK = 1024 * 1024
HASH_ALGORITHM = "SHA-256+MD5"


def hash_file(path: Path) -> Dict[str, str]:
    """Return {'md5':..., 'sha256':...} computed by streaming the file (constant RAM)."""
    md5 = hashlib.md5()  # noqa: S324 - MD5 is required by the spec for legacy comparison only
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            md5.update(chunk)
            sha.update(chunk)
    return {"md5": md5.hexdigest(), "sha256": sha.hexdigest()}


def hash_evidence_file(path: Path) -> Dict[str, object]:
    h = hash_file(path)
    return {**h, "hash_algorithm": HASH_ALGORITHM, "hashed_at": utcnow()}
