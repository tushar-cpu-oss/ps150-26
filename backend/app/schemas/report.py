from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import SafeId


class ReportRequest(BaseModel):
    case_id: SafeId
    evidence_ids: Optional[List[SafeId]] = Field(default=None, description="Omit to include all case evidence")


class ReportOut(BaseModel):
    report_id: str
    case_id: str
    evidence_ids: List[str]
    filename: str
    sha256: str
    file_size: int
    generated_at: datetime
    generated_by: str
    download_url: str
