import uuid
from pathlib import Path

from fastapi import APIRouter, Depends

from app.config import get_settings
from app.database import get_db
from app.routers.deps import get_actor, get_current_user
from app.schemas.acquisition import NetworkAcquisitionRequest
from app.services import case_service, custody_service, evidence_service, network_acquisition_service
from app.utils.errors import AppError

router = APIRouter(prefix="/api/acquisition", tags=["acquisition"], dependencies=[Depends(get_current_user)])

@router.post("/network")
def acquire_network(body: NetworkAcquisitionRequest, db=Depends(get_db), actor=Depends(get_actor)):
    case_service.get_case_doc(db, body.case_id)
    settings = get_settings()
    evidence_id = None
    # Use a temporary capture, then register it through the same immutable evidence workflow.
    tmp_dir = settings.processed_dir / "network_acquisition"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp = tmp_dir / f"capture_{uuid.uuid4().hex}.mp4"
    result = network_acquisition_service.acquire_stream(body.source_url, tmp, body.duration_seconds)
    try:
        doc = evidence_service.register_existing_evidence(
            db, body.case_id, tmp, original_filename=f"network_capture_{uuid.uuid4().hex[:8]}.mp4",
            camera_id=body.camera_id, recording_start=None, actor=actor,
            acquisition_method="standard_network_stream_capture",
            acquisition_source=result["source_url"],
        )
        evidence_id = doc["evidence_id"]
    finally:
        tmp.unlink(missing_ok=True)
    return {"evidence": doc, "acquisition": {**result, "evidence_id": evidence_id,
            "scope": "STANDARD_STREAM", "note": "This captures a stream exposed by the recorder/camera; it is not OEM-private DVR filesystem acquisition."}}
