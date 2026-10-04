from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import SafeId


class DeviceCreate(BaseModel):
    """Investigator-entered device information."""
    case_id: SafeId
    evidence_id: Optional[SafeId] = None
    manufacturer: str = Field(default="Unknown", max_length=100)
    model: Optional[str] = Field(default=None, max_length=100)
    serial_number: Optional[str] = Field(default=None, max_length=100)
    firmware: Optional[str] = Field(default=None, max_length=100)
    channels: Optional[int] = Field(default=None, ge=1, le=256)
    note: Optional[str] = Field(default=None, max_length=2000)


class DeviceDetectRequest(BaseModel):
    case_id: SafeId
    evidence_id: SafeId


class DeviceOut(BaseModel):
    device_id: str
    case_id: str
    evidence_id: Optional[str] = None
    manufacturer: str
    model: Optional[str] = None
    serial_number: Optional[str] = None
    firmware: Optional[str] = None
    channels: Optional[int] = None
    source: str
    confidence: Optional[str] = None  # null (unknown) | low | investigator_supplied - never a fabricated number
    identification_method: Optional[str] = None  # metadata_keyword_match | insufficient_evidence | investigator_entered
    confidence_basis: str
    note: Optional[str] = None
    created_at: datetime
