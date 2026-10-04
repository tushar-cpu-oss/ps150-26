from typing import List

from fastapi import APIRouter, Depends

from app.database import get_db
from app.routers.deps import get_current_user
from app.schemas.common import SafeId
from app.schemas.device import DeviceCreate, DeviceDetectRequest, DeviceOut
from app.services import device_service

router = APIRouter(prefix="/api/devices", tags=["devices"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=DeviceOut, status_code=201)
def create_device(body: DeviceCreate, db=Depends(get_db)):
    return device_service.create_device(db, body.model_dump())


@router.post("/detect", response_model=DeviceOut)
def detect_device(body: DeviceDetectRequest, db=Depends(get_db)):
    return device_service.detect_device(db, body.case_id, body.evidence_id)


@router.get("/{case_id}", response_model=List[DeviceOut])
def list_devices(case_id: SafeId, db=Depends(get_db)):
    return device_service.list_devices(db, case_id)
