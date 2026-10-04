"""Evidence acquisition (upload), hashing, metadata extraction, integrity verification."""
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.database import next_id
from app.services import case_service, custody_service, hashing_service, metadata_service, timeline_service
from app.utils import files
from app.utils.errors import AppError
from app.utils.mongo import to_api
from app.utils.timeutil import to_naive_utc, utcnow

log = logging.getLogger(__name__)


def get_evidence_doc(db, evidence_id: str) -> dict:
    doc = db.evidence.find_one({"evidence_id": evidence_id})
    if not doc:
        raise AppError(404, "EVIDENCE_NOT_FOUND", "Evidence was not found.")
    return doc


def resolve_path(doc: dict) -> Path:
    """Absolute path of the stored evidence file, guaranteed to be inside storage/evidence."""
    return files.safe_join(get_settings().evidence_dir, doc["stored_filename"])


def _parse_recording_start(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return to_naive_utc(datetime.fromisoformat(value.strip().replace("Z", "+00:00")))
    except ValueError:
        raise AppError(422, "INVALID_RECORDING_START", "recording_start must be an ISO-8601 datetime.")



def register_existing_evidence(db, case_id: str, source_path: Path, original_filename: str,
                                camera_id: Optional[str], recording_start: Optional[str], actor: str,
                                acquisition_method: str = "file_upload", acquisition_source: Optional[str] = None) -> dict:
    """Register an already-acquired file using the same hashing/metadata/custody path as upload.

    The source bytes are copied into the immutable evidence area before hashing.
    """
    settings = get_settings()
    case = case_service.get_case_doc(db, case_id)
    if case["status"] != "active":
        raise AppError(409, "CASE_NOT_ACTIVE", "Evidence can only be added to active cases.")
    original = files.sanitize_filename(original_filename)
    ext = files.get_extension(original)
    mime = files.validate_declared_mime(ext, None)
    evidence_id = next_id(db, "evidence", "EV-ROCKET", 6)
    stored_name = f"{evidence_id}_{uuid.uuid4().hex[:12]}.{ext}"
    settings.evidence_dir.mkdir(parents=True, exist_ok=True)
    dest = files.safe_join(settings.evidence_dir, stored_name)
    tmp = dest.with_name(dest.name + ".part")
    with Path(source_path).open("rb") as src, tmp.open("wb") as out:
        total = 0
        while True:
            chunk = src.read(1024 * 1024)
            if not chunk: break
            total += len(chunk)
            if total > settings.max_upload_bytes:
                tmp.unlink(missing_ok=True)
                raise AppError(413, "FILE_TOO_LARGE", "Acquired stream exceeds the configured evidence size limit.")
            out.write(chunk)
    os.replace(tmp, dest)
    os.chmod(dest, 0o440)
    hashes = hashing_service.hash_evidence_file(dest)
    metadata, metadata_error, processing_status = None, None, "metadata_extracted"
    try:
        metadata = metadata_service.extract_metadata(dest, original)
    except Exception as e:
        metadata_error = str(e); processing_status = "metadata_failed"
    investigator_start = _parse_recording_start(recording_start)
    if investigator_start:
        rec_start, rec_source, rec_confidence, rec_method = investigator_start, "investigator_supplied", "high", "user_supplied_recording_start"
    elif metadata and metadata.get("creation_time"):
        rec_start, rec_source, rec_confidence, rec_method = metadata["creation_time"], "container_creation_time", "medium", "container_creation_time"
    else:
        rec_start, rec_source, rec_confidence, rec_method = utcnow(), "acquisition_time_fallback", "low", "acquisition_time_fallback"
    now = utcnow()
    doc = {"evidence_id": evidence_id, "case_id": case_id, "original_filename": original, "stored_filename": stored_name,
           "extension": ext, "mime_type": mime, "file_size": total, "camera_id": camera_id,
           "recording_start": rec_start, "recording_start_source": rec_source,
           "recording_start_confidence": rec_confidence, "recording_start_method": rec_method, **hashes,
           "metadata": metadata, "metadata_error": metadata_error, "processing_status": processing_status,
           "analysis_status": "not_started", "latest_analysis_id": None, "last_verified_at": None,
           "last_verification_passed": None, "uploaded_by": actor, "created_at": now,
           "acquisition_method": acquisition_method, "acquisition_source": acquisition_source}
    db.evidence.insert_one(dict(doc))
    custody_service.record(db, case_id, evidence_id, "EVIDENCE_ACQUIRED", actor, hashes["sha256"],
                           f"Evidence '{original}' ({total} bytes) acquired via {acquisition_method}.")
    custody_service.record(db, case_id, evidence_id, "HASH_GENERATED", actor, hashes["sha256"],
                           f"SHA-256 and MD5 computed from acquired bytes. MD5={hashes['md5']}")
    if ext in files.VIDEO_EXTENSIONS:
        from datetime import timedelta
        timeline_service.add_system_event(db, case_id, evidence_id, "VIDEO_START", rec_start,
                                          f"Recording start ({rec_source})", 0.0, "acquisition", camera_id,
                                          {"timestamp_source": rec_source, "acquisition_method": acquisition_method})
        dur = (metadata or {}).get("duration")
        if dur:
            timeline_service.add_system_event(db, case_id, evidence_id, "VIDEO_END",
                                              rec_start + timedelta(seconds=float(dur)), "Recording end",
                                              float(dur), "metadata", camera_id, {"timestamp_source": rec_source})
    return to_api(doc)

def upload_evidence(db, case_id: str, upload, camera_id: Optional[str],
                    recording_start: Optional[str], actor: str) -> dict:
    settings = get_settings()
    case = case_service.get_case_doc(db, case_id)
    if case["status"] != "active":
        raise AppError(409, "CASE_NOT_ACTIVE", "Evidence can only be added to active cases.")

    original = files.sanitize_filename(upload.filename)
    ext = files.get_extension(original)
    mime = files.validate_declared_mime(ext, upload.content_type)
    investigator_start = _parse_recording_start(recording_start)

    evidence_id = next_id(db, "evidence", "EV-ROCKET", 6)
    stored_name = f"{evidence_id}_{uuid.uuid4().hex[:12]}.{ext}"
    settings.evidence_dir.mkdir(parents=True, exist_ok=True)
    dest = files.safe_join(settings.evidence_dir, stored_name)
    tmp = dest.with_name(dest.name + ".part")

    size = files.copy_with_limit(upload.file, tmp, settings.max_upload_bytes, ext)
    os.replace(tmp, dest)
    os.chmod(dest, 0o440)  # evidence is read-only from here on; analysis never writes to it

    hashes = hashing_service.hash_evidence_file(dest)  # real chunked hashes of the stored bytes

    metadata, metadata_error, processing_status = None, None, "metadata_extracted"
    try:
        metadata = metadata_service.extract_metadata(dest, original)
    except Exception as e:
        metadata_error = str(e)
        processing_status = "metadata_failed"
        log.warning("Metadata extraction failed for %s: %s", evidence_id, e)

    if investigator_start:
        rec_start, rec_source, rec_confidence, rec_method = investigator_start, "investigator_supplied", "high", "user_supplied_recording_start"
    elif metadata and metadata.get("creation_time"):
        rec_start, rec_source, rec_confidence, rec_method = metadata["creation_time"], "container_creation_time", "medium", "container_creation_time"
    else:
        rec_start, rec_source, rec_confidence, rec_method = utcnow(), "upload_time_fallback", "low", "upload_time_fallback"

    now = utcnow()
    doc = {
        "evidence_id": evidence_id, "case_id": case_id,
        "original_filename": original, "stored_filename": stored_name,
        "extension": ext, "mime_type": mime, "file_size": size,
        "camera_id": camera_id,
        "recording_start": rec_start, "recording_start_source": rec_source,
        "recording_start_confidence": rec_confidence, "recording_start_method": rec_method,
        **hashes,
        "metadata": metadata, "metadata_error": metadata_error,
        "processing_status": processing_status, "analysis_status": "not_started",
        "latest_analysis_id": None, "last_verified_at": None, "last_verification_passed": None,
        "uploaded_by": actor, "created_at": now,
    }
    db.evidence.insert_one(dict(doc))
    custody_service.record(db, case_id, evidence_id, "EVIDENCE_ACQUIRED", actor, hashes["sha256"],
                           f"Evidence '{original}' ({size} bytes) acquired via upload.")
    custody_service.record(db, case_id, evidence_id, "HASH_GENERATED", actor, hashes["sha256"],
                           f"SHA-256 and MD5 computed from stored file bytes. MD5={hashes['md5']}")
    if ext in files.VIDEO_EXTENSIONS:
        from datetime import timedelta
        timeline_service.add_system_event(db, case_id, evidence_id, "VIDEO_START", rec_start,
                                          f"Recording start ({rec_source})", 0.0, "metadata", camera_id,
                                          {"timestamp_source": rec_source})
        dur = (metadata or {}).get("duration")
        if dur:
            timeline_service.add_system_event(db, case_id, evidence_id, "VIDEO_END",
                                              rec_start + timedelta(seconds=float(dur)), "Recording end",
                                              float(dur), "metadata", camera_id, {"timestamp_source": rec_source})
    return to_api(doc)


def list_evidence(db, case_id: str) -> list:
    case_service.get_case_doc(db, case_id)
    return [to_api(d) for d in db.evidence.find({"case_id": case_id}).sort("created_at", 1)]


def get_evidence(db, evidence_id: str) -> dict:
    return to_api(get_evidence_doc(db, evidence_id))


def verify_evidence(db, evidence_id: str, actor: str) -> dict:
    doc = get_evidence_doc(db, evidence_id)
    now = utcnow()
    current = {"md5": None, "sha256": None}
    try:
        current = hashing_service.hash_file(resolve_path(doc))
        verified = current["sha256"] == doc["sha256"] and current["md5"] == doc["md5"]
        message = ("Integrity verified: current hashes match acquisition hashes." if verified else
                   "INTEGRITY FAILURE: current hashes differ from acquisition hashes.")
    except FileNotFoundError:
        verified, message = False, "INTEGRITY FAILURE: evidence file is missing from storage."
    db.evidence.update_one({"evidence_id": evidence_id},
                           {"$set": {"last_verified_at": now, "last_verification_passed": verified}})
    custody_service.record(db, doc["case_id"], evidence_id, "EVIDENCE_VERIFIED", actor, doc["sha256"],
                           f"Verification {'PASSED' if verified else 'FAILED'}. {message}")
    timeline_service.add_system_event(db, doc["case_id"], evidence_id, "EVIDENCE_VERIFIED", now,
                                      f"Integrity {'MATCH' if verified else 'TAMPERED'}", source="verification",
                                      camera_id=doc.get("camera_id"), extra={"verified": verified})
    return {
        "evidence_id": evidence_id, "verified": verified,
        "stored_sha256": doc["sha256"], "current_sha256": current["sha256"],
        "stored_md5": doc["md5"], "current_md5": current["md5"],
        "verified_at": now, "message": message,
        "integrity_status": "MATCH" if verified else "TAMPERED",
    }
