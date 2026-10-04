from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.utils.errors import AppError
from app.utils.ranges import parse_range

from app.database import get_db
from app.routers.deps import get_actor, get_current_user
from app.schemas.common import SafeId
from app.schemas.evidence import EvidenceOut, VerifyResponse
from app.services import evidence_service

router = APIRouter(prefix="/api/evidence", tags=["evidence"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=List[EvidenceOut])
def list_case_evidence(case_id: SafeId = Query(...), db=Depends(get_db)):
    """List evidence belonging to a case. This is the case-workspace read path for EvidenceOut records."""
    return evidence_service.list_evidence(db, case_id)

@router.post("/upload", response_model=EvidenceOut, status_code=201)
def upload_evidence(case_id: SafeId = Form(...), file: UploadFile = File(...),
                    camera_id: Optional[str] = Form(None, max_length=100),
                    recording_start: Optional[str] = Form(None, description="Optional ISO-8601 recording start time"),
                    db=Depends(get_db), actor: str = Depends(get_actor)):
    return evidence_service.upload_evidence(db, case_id, file, camera_id, recording_start, actor)


@router.get("/{evidence_id}", response_model=EvidenceOut)
def get_evidence(evidence_id: SafeId, db=Depends(get_db)):
    return evidence_service.get_evidence(db, evidence_id)


@router.post("/{evidence_id}/verify", response_model=VerifyResponse)
def verify_evidence(evidence_id: SafeId, db=Depends(get_db), actor: str = Depends(get_actor)):
    return evidence_service.verify_evidence(db, evidence_id, actor)


_MEDIA_TYPES = {"mp4": "video/mp4", "mkv": "video/x-matroska", "avi": "video/x-msvideo", "mov": "video/quicktime",
                "wav": "audio/wav", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}


@router.get("/{evidence_id}/stream", responses={206: {"description": "Partial content (Range request)"},
                                                 416: {"description": "Range not satisfiable"}})
def stream_evidence(evidence_id: SafeId, request: Request, db=Depends(get_db)):
    """Serve the ORIGINAL stored file read-only with HTTP Range support (play/pause/seek in <video>).
    For <video src>, pass `?token=<jwt>` since media tags cannot send an Authorization header."""
    doc = evidence_service.get_evidence_doc(db, evidence_id)
    path = evidence_service.resolve_path(doc)
    if not path.exists():
        raise AppError(404, "EVIDENCE_FILE_MISSING", "Evidence file is missing from storage.")
    size = path.stat().st_size
    rng = parse_range(request.headers.get("range"), size)
    start, end = rng if rng else (0, size - 1)
    length = end - start + 1

    def iterfile():
        with open(path, "rb") as f:  # read-only
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    headers = {"Accept-Ranges": "bytes", "Content-Length": str(length), "Cache-Control": "private, no-store"}
    if rng:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return StreamingResponse(iterfile(), status_code=206 if rng else 200, headers=headers,
                             media_type=_MEDIA_TYPES.get(doc["extension"], "application/octet-stream"))
