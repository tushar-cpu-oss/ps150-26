from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class EvidenceOut(BaseModel):
    evidence_id: str
    case_id: str
    original_filename: str
    extension: str
    mime_type: str
    file_size: int
    camera_id: Optional[str] = None
    recording_start: Optional[datetime] = None
    recording_start_source: Optional[str] = None
    md5: str
    sha256: str
    hash_algorithm: str
    hashed_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    metadata_error: Optional[str] = None
    processing_status: str
    analysis_status: str
    latest_analysis_id: Optional[str] = None
    last_verified_at: Optional[datetime] = None
    last_verification_passed: Optional[bool] = None
    uploaded_by: str
    created_at: datetime


class VerifyResponse(BaseModel):
    evidence_id: str
    verified: bool
    stored_sha256: str
    current_sha256: Optional[str] = None
    stored_md5: str
    current_md5: Optional[str] = None
    verified_at: datetime
    message: str
    integrity_status: str = "MATCH"  # MATCH | TAMPERED (missing file counts as TAMPERED)
