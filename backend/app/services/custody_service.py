"""Append-only chain-of-custody log."""
import uuid
from typing import List, Optional

from app.models.collections import CUSTODY_ACTIONS
from app.utils.mongo import to_api
from app.utils.timeutil import utcnow


def record(db, case_id: str, evidence_id: str, action: str, actor: str,
           sha256: Optional[str], description: str) -> dict:
    assert action in CUSTODY_ACTIONS, f"unknown custody action {action}"
    doc = {
        "actor_user_id": getattr(actor, "user_id", None),  # set only from the authenticated JWT user
        "custody_id": str(uuid.uuid4()),
        "case_id": case_id,
        "evidence_id": evidence_id,
        "action": action,
        "actor": str(actor),
        "timestamp": utcnow(),
        "sha256": sha256,
        "description": description,
    }
    db.chain_of_custody.insert_one(dict(doc))
    return doc


def list_records(db, evidence_id: str) -> List[dict]:
    cur = db.chain_of_custody.find({"evidence_id": evidence_id}).sort([("timestamp", 1)])
    out = []
    for d in cur:
        r = to_api(d)
        r["actor_name"] = r.get("actor")
        out.append(r)
    return out
