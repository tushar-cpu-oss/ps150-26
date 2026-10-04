from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class CustodyRecordOut(BaseModel):
    custody_id: str
    case_id: str
    evidence_id: str
    action: str
    actor: str
    actor_name: Optional[str] = None
    actor_user_id: Optional[str] = None
    timestamp: datetime
    sha256: Optional[str] = None
    description: str


class CustodyResponse(BaseModel):
    evidence_id: str
    count: int
    records: List[CustodyRecordOut]
