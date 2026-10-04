from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.common import SafeId

class NetworkAcquisitionRequest(BaseModel):
    case_id: SafeId
    source_url: str = Field(..., min_length=8, max_length=2048)
    camera_id: Optional[str] = Field(None, max_length=100)
    duration_seconds: int = Field(default=30, ge=1, le=300)
