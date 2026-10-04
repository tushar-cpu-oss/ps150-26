from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

CaseStatus = Literal["active", "archived", "closed"]


class CaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    # NOTE: the investigator is always the authenticated user; any value sent here is ignored.
    investigator: Optional[str] = Field(default=None, max_length=200)


class CaseUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    status: Optional[CaseStatus] = None


class CaseOut(BaseModel):
    case_id: str
    case_number: Optional[str] = None
    name: str
    description: str
    investigator: str
    investigator_id: Optional[str] = None
    status: CaseStatus
    created_at: datetime
    updated_at: datetime
    evidence_count: int = 0
    event_count: int = 0
