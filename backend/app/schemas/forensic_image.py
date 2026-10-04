from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import SafeId

class ForensicImageOut(BaseModel):
    image_id: str
    case_id: str
    filename: str
    image_type: Optional[str] = None
    size_bytes: int
    md5: str
    sha256: str
    parser_status: str
    created_at: datetime

class RecoveryRequest(BaseModel):
    image_id: SafeId
    max_items: int = Field(default=100, ge=1, le=1000)

class RecoveryOut(BaseModel):
    image_id: str
    status: str
    recovered_items: int
    artifacts: List[Dict[str, Any]] = []
    message: str
