import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.config import get_settings
from app.database import get_db, next_id
from app.routers.deps import get_actor, get_current_user
from app.schemas.common import SafeId
from app.schemas.forensic_image import ForensicImageOut, RecoveryOut, RecoveryRequest
from app.services import case_service, custody_service, forensic_image_service, hashing_service, recovery_service, oem_baseline_service
from app.utils.errors import AppError
from app.utils.files import safe_join, sanitize_filename
from app.utils.mongo import to_api
from app.utils.timeutil import utcnow

router = APIRouter(prefix="/api/forensic-images", tags=["forensic-images"], dependencies=[Depends(get_current_user)])


def _path(doc: dict) -> Path:
    return safe_join(get_settings().forensic_images_dir, doc["stored_filename"])


@router.post("/ingest", response_model=ForensicImageOut, status_code=201)
def ingest(case_id: SafeId = Form(...), file: UploadFile = File(...),
           db=Depends(get_db), actor=Depends(get_actor)):
    case_service.get_case_doc(db, case_id)
    original = sanitize_filename(file.filename)
    ext = Path(original).suffix.lower().lstrip(".")
    if ext not in forensic_image_service.IMAGE_EXTENSIONS:
        raise AppError(415, "UNSUPPORTED_IMAGE_TYPE", "Supported forensic images: .dd, .img, .raw, .e01, .001")
    s = get_settings(); s.forensic_images_dir.mkdir(parents=True, exist_ok=True)
    image_id = next_id(db, "forensic_image", "IMG-ROCKET", 6)
    stored = f"{image_id}_{uuid.uuid4().hex[:12]}.{ext}"
    dest = safe_join(s.forensic_images_dir, stored); tmp = dest.with_name(dest.name + ".part")
    with tmp.open("wb") as out:
        total = 0
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk: break
            total += len(chunk)
            if total > s.max_upload_bytes * 4:
                tmp.unlink(missing_ok=True)
                raise AppError(413, "IMAGE_TOO_LARGE", "Forensic image exceeds the configured image limit (4x evidence limit).")
            out.write(chunk)
    if total == 0:
        tmp.unlink(missing_ok=True); raise AppError(400, "EMPTY_FILE", "Forensic image is empty.")
    os.replace(tmp, dest); os.chmod(dest, 0o440)
    artifact = forensic_image_service.ingest_image_artifact(dest)
    doc = {"image_id": image_id, "case_id": case_id, "filename": original, "stored_filename": stored,
           **artifact.__dict__, "path": None, "created_at": utcnow(), "uploaded_by": str(actor)}
    db.forensic_images.insert_one(dict(doc))
    custody_service.record(db, case_id, image_id, "EVIDENCE_ACQUIRED", actor, artifact.sha256,
                           f"Forensic image ingested read-only as {image_id}; original bytes preserved.")
    return to_api(doc)


@router.get("/{image_id}", response_model=ForensicImageOut)
def get_image(image_id: SafeId, db=Depends(get_db)):
    doc = db.forensic_images.find_one({"image_id": image_id})
    if not doc: raise AppError(404, "IMAGE_NOT_FOUND", "Forensic image was not found.")
    return to_api(doc)


@router.get("/{image_id}/inspect")
def inspect(image_id: SafeId, db=Depends(get_db)):
    doc = db.forensic_images.find_one({"image_id": image_id})
    if not doc: raise AppError(404, "IMAGE_NOT_FOUND", "Forensic image was not found.")
    result = forensic_image_service.inspect_image(_path(doc))
    return {"image_id": image_id, **result}


@router.get("/{image_id}/oem-baseline")
def oem_baseline(image_id: SafeId, db=Depends(get_db)):
    doc = db.forensic_images.find_one({"image_id": image_id})
    if not doc: raise AppError(404, "IMAGE_NOT_FOUND", "Forensic image was not found.")
    return {"image_id": image_id, **oem_baseline_service.baseline_inspect(_path(doc))}


@router.post("/{image_id}/recover", response_model=RecoveryOut)
def recover(image_id: SafeId, body: RecoveryRequest, db=Depends(get_db), actor=Depends(get_actor)):
    if body.image_id != image_id: raise AppError(400, "IMAGE_ID_MISMATCH", "Request image_id does not match path.")
    doc = db.forensic_images.find_one({"image_id": image_id})
    if not doc: raise AppError(404, "IMAGE_NOT_FOUND", "Forensic image was not found.")
    out = get_settings().processed_dir / "recovered" / image_id
    image_path = _path(doc)
    result = recovery_service.carve_standard_video(image_path, out, body.max_items)
    deleted = forensic_image_service.find_deleted_standard_files(image_path)
    result_doc = {"image_id": image_id, "status": "COMPLETED" if result or deleted else "NO_RECOVERABLE_STANDARD_VIDEO_FOUND",
                  "recovered_items": len(result), "deleted_files_found": deleted, "artifacts": result,
                  "message": "Standard signature carving completed; Sleuth Kit deleted-file enumeration is included when available. OEM DVR deleted-record reconstruction is not claimed."}
    custody_service.record(db, doc["case_id"], image_id, "ANALYSIS_COMPLETED", actor, doc["sha256"],
                           f"Standard signature carving executed; recovered_items={len(result)}")
    return result_doc
