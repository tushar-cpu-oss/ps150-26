from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from fastapi.responses import FileResponse

from app.config import get_settings
from app.utils.errors import AppError
from app.utils.files import safe_join

from app.database import get_db
from app.routers.deps import get_actor, get_current_user
from app.schemas.analysis import (AnalysisOut, AnalysisRequest, AnalysisStarted, SearchRequest, SearchResponse)
from app.schemas.common import SafeId
from app.services import analysis_service, timeline_service

router = APIRouter(prefix="/api/analysis", tags=["analysis"], dependencies=[Depends(get_current_user)])


@router.post("/video", response_model=AnalysisStarted, status_code=202)
def start_video_analysis(body: AnalysisRequest, background: BackgroundTasks,
                         db=Depends(get_db), actor: str = Depends(get_actor)):
    job = analysis_service.create_job(db, body.evidence_id, body.options.model_dump(), actor)
    background.add_task(analysis_service.run_job, job["analysis_id"], actor)
    return {"analysis_id": job["analysis_id"], "status": job["status"]}


@router.post("/search", response_model=SearchResponse)
def search(body: SearchRequest, db=Depends(get_db)):
    results = timeline_service.search(db, body.model_dump())
    return {"query_mode": "structured", "count": len(results), "results": results}


@router.get("/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: SafeId, db=Depends(get_db)):
    return analysis_service.get_job(db, analysis_id)


@router.get("/{analysis_id}/snapshots", tags=["analysis"])
def list_snapshots(analysis_id: SafeId, request: Request, db=Depends(get_db)):
    """Annotated frames (bbox/class/confidence/timestamp drawn) for frames where YOLO detected objects.
    `image_url` is a path on this API; media tags may append `?token=<jwt>`."""
    return analysis_service.list_snapshots(db, analysis_id)


@router.get("/{analysis_id}/snapshots/{filename}", tags=["analysis"], response_class=FileResponse)
def get_snapshot_image(analysis_id: SafeId, filename: str, db=Depends(get_db)):
    from app.ml.snapshots import SNAPSHOT_RE
    analysis_service.get_job(db, analysis_id)
    if not SNAPSHOT_RE.match(filename):
        raise AppError(400, "INVALID_FILENAME", "Invalid snapshot filename.")
    path = safe_join(get_settings().snapshots_dir, analysis_id, filename)
    if not path.exists():
        raise AppError(404, "SNAPSHOT_NOT_FOUND", "Snapshot was not found.")
    return FileResponse(path, media_type="image/jpeg")
