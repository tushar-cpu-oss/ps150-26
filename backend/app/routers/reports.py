from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.config import get_settings
from app.database import get_db
from app.routers.deps import get_actor, get_current_user
from app.schemas.common import SafeId
from app.schemas.report import ReportOut, ReportRequest
from app.services import report_service
from app.utils.errors import AppError
from app.utils.files import safe_join

router = APIRouter(prefix="/api/reports", tags=["reports"], dependencies=[Depends(get_current_user)])


@router.post("/generate", response_model=ReportOut, status_code=201)
def generate_report(body: ReportRequest, db=Depends(get_db), actor: str = Depends(get_actor)):
    return report_service.generate_report(db, body.case_id, body.evidence_ids, actor)


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: SafeId, db=Depends(get_db)):
    return report_service.get_report(db, report_id)


@router.get("/{report_id}/download")
def download_report(report_id: SafeId, db=Depends(get_db)):
    rep = report_service.get_report(db, report_id)
    path = safe_join(get_settings().reports_dir, rep["filename"])
    if not path.exists():
        raise AppError(404, "REPORT_FILE_MISSING", "Report file is missing from storage.")
    return FileResponse(path, media_type="application/pdf", filename=rep["filename"])
