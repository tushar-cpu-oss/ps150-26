from typing import List, Optional

from app.database import next_id
from app.utils.errors import AppError
from app.utils.mongo import to_api
from app.utils.timeutil import utcnow


def _with_counts(db, doc: dict) -> dict:
    out = to_api(doc)
    out["evidence_count"] = db.evidence.count_documents({"case_id": doc["case_id"]})
    # consistent with the timeline: only the latest completed analysis per evidence counts
    latest = [e["latest_analysis_id"] for e in db.evidence.find({"case_id": doc["case_id"],
                                                                  "latest_analysis_id": {"$ne": None}})]
    out["event_count"] = db.timeline_events.count_documents(
        {"case_id": doc["case_id"], "$or": [{"analysis_id": {"$in": latest}}, {"analysis_id": None}]})
    return out


def get_case_doc(db, case_id: str) -> dict:
    doc = db.cases.find_one({"case_id": case_id})
    if not doc:
        raise AppError(404, "CASE_NOT_FOUND", "Case was not found.")
    return doc


def _can_access(case: dict, user: Optional[dict]) -> bool:
    if user is None or user.get("role") == "admin":
        return True
    return case.get("investigator_id") in (None, user["user_id"])  # legacy cases have no owner


def create_case(db, name: str, description: str, user: dict) -> dict:
    """The investigator is the authenticated user - never a value supplied by the client."""
    now = utcnow()
    case_id = next_id(db, "case", "CASE-ROCKET", 4)
    doc = {
        "case_id": case_id, "case_number": case_id,
        "name": name, "description": description,
        "investigator": user["full_name"], "investigator_id": user["user_id"],
        "status": "active", "created_at": now, "updated_at": now,
    }
    db.cases.insert_one(dict(doc))
    return _with_counts(db, doc)


def list_cases(db, status: Optional[str], skip: int, limit: int, user: Optional[dict] = None) -> List[dict]:
    q = {"status": status} if status else {}
    if user is not None and user.get("role") != "admin":
        q["$or"] = [{"investigator_id": user["user_id"]}, {"investigator_id": {"$exists": False}}]
    cur = db.cases.find(q).sort("created_at", -1).skip(skip).limit(limit)
    return [_with_counts(db, d) for d in cur]


def get_case(db, case_id: str, user: Optional[dict] = None) -> dict:
    doc = get_case_doc(db, case_id)
    if not _can_access(doc, user):
        raise AppError(403, "FORBIDDEN", "You do not have access to this case.")
    return _with_counts(db, doc)


def update_case(db, case_id: str, changes: dict, user: Optional[dict] = None) -> dict:
    doc = get_case_doc(db, case_id)
    if not _can_access(doc, user):
        raise AppError(403, "FORBIDDEN", "You do not have access to this case.")
    changes = {k: v for k, v in changes.items() if v is not None}
    if changes:
        changes["updated_at"] = utcnow()
        db.cases.update_one({"case_id": case_id}, {"$set": changes})
    return get_case(db, case_id, user)


def delete_case(db, case_id: str, user: Optional[dict] = None) -> None:
    doc = get_case_doc(db, case_id)
    if not _can_access(doc, user):
        raise AppError(403, "FORBIDDEN", "You do not have access to this case.")
    if db.evidence.count_documents({"case_id": case_id}) > 0:
        raise AppError(
            409, "CASE_HAS_EVIDENCE",
            "Cases that contain evidence cannot be deleted (chain of custody must be preserved). "
            "Set the case status to 'archived' or 'closed' instead.")
    db.cases.delete_one({"case_id": case_id})
