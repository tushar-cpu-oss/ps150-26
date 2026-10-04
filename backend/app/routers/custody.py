from fastapi import APIRouter, Depends

from app.database import get_db
from app.routers.deps import get_current_user
from app.schemas.common import SafeId
from app.schemas.custody import CustodyResponse
from app.services import custody_service, evidence_service

router = APIRouter(prefix="/api/chain-of-custody", tags=["chain-of-custody"], dependencies=[Depends(get_current_user)])


@router.get("/{evidence_id}", response_model=CustodyResponse)
def get_chain_of_custody(evidence_id: SafeId, db=Depends(get_db)):
    evidence_service.get_evidence_doc(db, evidence_id)  # 404 if unknown
    records = custody_service.list_records(db, evidence_id)
    return {"evidence_id": evidence_id, "count": len(records), "records": records}
