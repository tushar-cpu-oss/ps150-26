from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.routers.deps import get_current_user
from app.schemas.common import SafeId
from app.schemas.timeline import TimelineResponse
from app.services import timeline_service

router = APIRouter(prefix="/api/timeline", tags=["timeline"], dependencies=[Depends(get_current_user)])


@router.get("/{case_id}", response_model=TimelineResponse)
def get_timeline(case_id: SafeId,
                 start_time: Optional[str] = Query(None, description="ISO datetime or HH:MM:SS (UTC)"),
                 end_time: Optional[str] = Query(None),
                 event_type: Optional[str] = Query(None, max_length=50),
                 camera_id: Optional[str] = Query(None, max_length=100),
                 min_confidence: Optional[float] = Query(None, ge=0, le=1),
                 evidence_id: Optional[SafeId] = None, analysis_id: Optional[SafeId] = None,
                 limit: int = Query(1000, ge=1, le=20000), db=Depends(get_db)):
    events = timeline_service.query_events(db, case_id, start_time, end_time, event_type, camera_id,
                                           min_confidence, evidence_id, analysis_id, None, limit)
    return {"case_id": case_id, "count": len(events), "events": events}


@router.get("/{case_id}/correlation", tags=["correlation"])
def get_correlation(case_id: SafeId, window_seconds: float = Query(30.0, gt=0, le=3600),
                    class_name: Optional[str] = Query(None, max_length=50), db=Depends(get_db)):
    """Cross-camera TEMPORAL correlation: same object class on different cameras within a time window.
    This is not identity matching."""
    events = timeline_service.query_events(db, case_id, class_name=class_name, limit=20000)
    groups = timeline_service.correlate(events, window_seconds, class_name)
    return {"case_id": case_id, "count": len(groups), "disclaimer": timeline_service.CORRELATION_DISCLAIMER,
            "groups": groups}
