from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TimelineEventOut(BaseModel):
    event_id: str
    case_id: str
    evidence_id: str
    analysis_id: Optional[str] = None
    timestamp: datetime                       # absolute time (see metadata.timestamp_source)
    video_time_seconds: Optional[float] = None  # seconds; set video.currentTime = this value to seek
    event_type: str
    class_name: Optional[str] = None
    confidence: Optional[float] = None
    frame_number: Optional[int] = None
    camera_id: Optional[str] = None
    motion_score: Optional[float] = None
    detection_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


class TimelineResponse(BaseModel):
    case_id: str
    count: int
    events: List[TimelineEventOut]
