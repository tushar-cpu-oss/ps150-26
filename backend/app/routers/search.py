from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.routers.deps import get_current_user
from app.schemas.analysis import SearchResponse
from app.schemas.common import SafeId
from app.services import timeline_service

router = APIRouter(prefix="/api/search", tags=["search"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=SearchResponse)
def structured_search(case_id: SafeId, object: Optional[str] = Query(None, max_length=50, description="e.g. person, car, or 'motion'"),
                      camera: Optional[str] = Query(None, max_length=100),
                      from_: Optional[str] = Query(None, alias="from", description="ISO datetime or HH:MM[:SS] (UTC)"),
                      to: Optional[str] = Query(None), min_confidence: Optional[float] = Query(None, ge=0, le=1),
                      evidence_id: Optional[SafeId] = None, limit: int = Query(500, ge=1, le=5000),
                      db=Depends(get_db)):
    """STRUCTURED search over real detection/motion events. Natural-language queries are NOT implemented."""
    results = timeline_service.search(db, {"case_id": case_id, "object_type": object, "camera_id": camera,
                                           "start_time": from_, "end_time": to, "minimum_confidence": min_confidence,
                                           "evidence_id": evidence_id, "limit": limit})
    return {"query_mode": "structured", "count": len(results), "results": results}
