"""Evidence-preserving recovery of standard video signatures from raw images/files.

This is real file carving, not simulated recovery. It deliberately does not claim to recover
OEM DVR database records or reconstruct proprietary filesystem metadata. Recovered fragments are
stored as separate working artifacts and independently hashed.
"""
import hashlib
import os
from pathlib import Path
from typing import Dict, Iterable, List

from app.services import forensic_image_service

SIGNATURES = {
    "jpg": [(b"\xff\xd8\xff", b"\xff\xd9")],
    "png": [(b"\x89PNG\r\n\x1a\n", b"IEND\xaeB`\x82")],
    "avi": [(b"RIFF", b"\x00\x00\x00\x00")],
    "mp4": [(b"ftyp", None)],
    "mkv": [(b"\x1a\x45\xdf\xa3", None)],
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _find_all(data: bytes, needle: bytes, start: int = 0) -> Iterable[int]:
    pos = start
    while True:
        pos = data.find(needle, pos)
        if pos < 0:
            return
        yield pos
        pos += max(1, len(needle))


def carve_standard_video(image_path: Path, output_dir: Path, max_items: int = 100) -> List[Dict]:
    """Carve obvious container signatures from a raw image. Best-effort and intentionally conservative."""
    if not image_path.is_file():
        raise FileNotFoundError(str(image_path))
    output_dir.mkdir(parents=True, exist_ok=True)
    data = image_path.read_bytes()
    hits = []
    # MP4: locate 'ftyp' and include the preceding 4-byte size field when present.
    for pos in _find_all(data, b"ftyp"):
        start = max(0, pos - 4)
        if start + 8 <= len(data):
            size = int.from_bytes(data[start:start + 4], "big")
            if 8 <= size <= len(data) - start:
                end = start + size
                # Find the next top-level atom boundary; otherwise cap at 512 MiB.
                cursor = end
                while cursor + 8 <= len(data):
                    atom_size = int.from_bytes(data[cursor:cursor + 4], "big")
                    if atom_size < 8 or cursor + atom_size > len(data): break
                    if data[cursor + 4:cursor + 8] in (b"moov", b"mdat", b"free", b"wide", b"skip"):
                        cursor += atom_size
                    else: break
                end = max(end, cursor)
                if end - start >= 1024:
                    hits.append((start, end, "mp4"))
    # MKV: recover a bounded chunk because EBML has no simple footer.
    for pos in _find_all(data, b"\x1a\x45\xdf\xa3"):
        end = min(len(data), pos + 512 * 1024 * 1024)
        if end - pos >= 1024:
            hits.append((pos, end, "mkv"))
    # AVI/JPEG/PNG are included because they have unambiguous endings where practical.
    for pos in _find_all(data, b"RIFF"):
        if pos + 12 <= len(data) and data[pos + 8:pos + 12] == b"AVI ":
            size = int.from_bytes(data[pos + 4:pos + 8], "little") + 8
            end = min(len(data), pos + size)
            if end - pos >= 1024: hits.append((pos, end, "avi"))
    for pos in _find_all(data, b"\xff\xd8\xff"):
        end = data.find(b"\xff\xd9", pos + 3)
        if end >= 0 and end + 2 - pos >= 256: hits.append((pos, end + 2, "jpg"))
    for pos in _find_all(data, b"\x89PNG\r\n\x1a\n"):
        end = data.find(b"IEND\xaeB`\x82", pos + 8)
        if end >= 0: hits.append((pos, end + 8, "png"))

    # Deduplicate overlapping ranges and cap output.
    unique = []
    seen = set()
    for start, end, ext in sorted(hits, key=lambda x: (x[0], -(x[1] - x[0]))):
        key = (start, end, ext)
        if key in seen: continue
        seen.add(key)
        if any(start >= a and end <= b for a, b, _ in unique): continue
        unique.append(key)
        if len(unique) >= max_items: break

    results = []
    with image_path.open("rb") as src:
        for idx, (start, end, ext) in enumerate(unique, 1):
            src.seek(start)
            out = output_dir / f"recovered_{idx:04d}_{start:012x}.{ext}"
            remaining = end - start
            with out.open("wb") as dst:
                while remaining:
                    chunk = src.read(min(1024 * 1024, remaining))
                    if not chunk: break
                    dst.write(chunk); remaining -= len(chunk)
            if out.stat().st_size:
                results.append({"artifact": str(out), "extension": ext, "offset": start,
                                "size_bytes": out.stat().st_size, "sha256": _sha256(out),
                                "recovery_method": "standard_signature_carving"})
    return results


def attempt_recovery(evidence_id: str, image_path: Path | None = None, output_dir: Path | None = None) -> dict:
    if image_path is None:
        return {"evidence_id": evidence_id, "status": "REQUIRES_IMAGE", "recovered_items": 0,
                "message": "Provide a forensic/raw image for signature carving. OEM deleted-record recovery is not claimed."}
    outdir = output_dir or image_path.parent / "recovered"
    deleted = forensic_image_service.find_deleted_standard_files(image_path)
    results = carve_standard_video(image_path, outdir)
    status = "COMPLETED" if results or deleted else "NO_RECOVERABLE_STANDARD_VIDEO_FOUND"
    return {"evidence_id": evidence_id, "status": status, "recovered_items": len(results),
            "deleted_files_found": deleted, "artifacts": results,
            "message": "Standard signature carving completed. Sleuth Kit deleted-file enumeration is included when available; OEM DVR deleted-record reconstruction is not claimed."}
