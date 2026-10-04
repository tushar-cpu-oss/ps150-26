from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response

from app.database import get_db
from app.routers.deps import get_current_user
from app.schemas.case import CaseCreate, CaseOut, CaseStatus, CaseUpdate
from app.schemas.common import SafeId
from app.services import case_service

router = APIRouter(prefix="/api/cases", tags=["cases"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=CaseOut, status_code=201)
def create_case(body: CaseCreate, db=Depends(get_db), user: dict = Depends(get_current_user)):
    return case_service.create_case(db, body.name, body.description, user)


@router.get("", response_model=List[CaseOut])
def list_cases(status: Optional[CaseStatus] = None, skip: int = Query(0, ge=0),
               limit: int = Query(50, ge=1, le=200), db=Depends(get_db),
               user: dict = Depends(get_current_user)):
    return case_service.list_cases(db, status, skip, limit, user)


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: SafeId, db=Depends(get_db), user: dict = Depends(get_current_user)):
    return case_service.get_case(db, case_id, user)


@router.put("/{case_id}", response_model=CaseOut)
@router.patch("/{case_id}", response_model=CaseOut, include_in_schema=False)
def update_case(case_id: SafeId, body: CaseUpdate, db=Depends(get_db), user: dict = Depends(get_current_user)):
    """Partial update (name, description, status). Also reachable as PATCH."""
    return case_service.update_case(db, case_id, body.model_dump(exclude_unset=True), user)


@router.delete("/{case_id}", status_code=204)
def delete_case(case_id: SafeId, db=Depends(get_db), user: dict = Depends(get_current_user)):
    case_service.delete_case(db, case_id, user)
    return Response(status_code=204)
