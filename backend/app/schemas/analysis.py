from datetime import datetime
from typing import Any, Dict, List, Optional

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import SafeId
from app.schemas.timeline import TimelineEventOut


class AnalysisOptions(BaseModel):
    object_detection: bool = True
    motion_detection: bool = True
    face_detection: bool = True
    object_tracking: bool = False
    preset: Optional[Literal["fast", "balanced", "deep"]] = Field(
        default=None, description="fast=1, balanced=2, deep=5 frames/sec (ignored if frame_sample_rate is set)")
    frame_sample_rate: Optional[float] = Field(default=None, gt=0, le=60,
                                               description="Frames analysed per second; default from FRAME_SAMPLE_RATE")
    confidence_threshold: Optional[float] = Field(default=None, ge=0, le=1,
                                                  description="Default from YOLO_CONFIDENCE_THRESHOLD")


class AnalysisRequest(BaseModel):
    evidence_id: SafeId
    options: AnalysisOptions = Field(default_factory=AnalysisOptions)


class AnalysisStarted(BaseModel):
    analysis_id: str
    status: str


class AnalysisOut(BaseModel):
    analysis_id: str
    case_id: str
    evidence_id: str
    status: str
    options: Dict[str, Any]
    model: Optional[str] = None
    model_version: Optional[str] = None
    snapshots: int = 0
    progress: float = 0.0
    stage: Optional[str] = Field(default=None, description="Active pipeline stage, or null when idle/finished")
    stages: List[Dict[str, Any]] = Field(default_factory=list,
                                         description="Ordered stages: pending|running|completed|skipped|failed")
    modules: Dict[str, Any] = {}
    warnings: List[str] = []
    counts: Dict[str, int] = {}
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class SearchRequest(BaseModel):
    """Structured search (v1). Natural-language parsing can later populate these same fields."""
    case_id: SafeId
    object_type: Optional[str] = Field(default=None, max_length=50, description="e.g. person, car, or 'motion'")
    start_time: Optional[str] = Field(default=None, description="ISO datetime or HH:MM:SS time of day (UTC)")
    end_time: Optional[str] = None
    minimum_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    evidence_id: Optional[SafeId] = None
    camera_id: Optional[str] = Field(default=None, max_length=100)
    limit: int = Field(default=500, ge=1, le=5000)


class SearchResponse(BaseModel):
    query_mode: str = "structured"
    count: int
    results: List[TimelineEventOut]
