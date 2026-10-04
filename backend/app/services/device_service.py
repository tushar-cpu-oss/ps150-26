"""Device identification.

IMPLEMENTED: keyword inference from real evidence metadata tags + filename (low confidence),
             and manual investigator entry.
OEM proprietary DVR/NVR filesystem parsing and vendor acquisition protocols remain unsupported; evidence-based identification and file/image acquisition are implemented.
"""
from typing import List

from app.database import next_id
from app.services import case_service, evidence_service
from app.services.device_inference import UNKNOWN_NOTE, infer_from_metadata  # noqa: F401
from app.utils.errors import AppError
from app.utils.mongo import to_api
from app.utils.timeutil import utcnow


def detect_device(db, case_id: str, evidence_id: str) -> dict:
    case_service.get_case_doc(db, case_id)
    ev = evidence_service.get_evidence_doc(db, evidence_id)
    if ev["case_id"] != case_id:
        raise AppError(400, "EVIDENCE_CASE_MISMATCH", "Evidence does not belong to this case.")
    inferred = infer_from_metadata(ev.get("metadata"), ev["original_filename"])
    fields = {**inferred, "channels": None, "source": "metadata_inference", "note": None}
    existing = db.devices.find_one({"evidence_id": evidence_id, "source": "metadata_inference"})
    if existing:
        db.devices.update_one({"device_id": existing["device_id"]}, {"$set": fields})
        return to_api(db.devices.find_one({"device_id": existing["device_id"]}))
    doc = {"device_id": next_id(db, "device", "DEV-ROCKET", 4), "case_id": case_id,
           "evidence_id": evidence_id, **fields, "created_at": utcnow()}
    db.devices.insert_one(dict(doc))
    return to_api(doc)


def create_device(db, data: dict) -> dict:
    case_service.get_case_doc(db, data["case_id"])
    if data.get("evidence_id"):
        ev = evidence_service.get_evidence_doc(db, data["evidence_id"])
        if ev["case_id"] != data["case_id"]:
            raise AppError(400, "EVIDENCE_CASE_MISMATCH", "Evidence does not belong to this case.")
    doc = {
        "device_id": next_id(db, "device", "DEV-ROCKET", 4),
        "case_id": data["case_id"], "evidence_id": data.get("evidence_id"),
        "manufacturer": data.get("manufacturer") or "Unknown", "model": data.get("model"),
        "serial_number": data.get("serial_number"), "firmware": data.get("firmware"),
        "channels": data.get("channels"), "source": "investigator_entered",
        "confidence": "investigator_supplied", "identification_method": "investigator_entered",
        "confidence_basis": "Entered manually by the investigator; not verified by the platform.",
        "note": data.get("note"), "created_at": utcnow(),
    }
    db.devices.insert_one(dict(doc))
    return to_api(doc)


def list_devices(db, case_id: str) -> List[dict]:
    case_service.get_case_doc(db, case_id)
    return [to_api(d) for d in db.devices.find({"case_id": case_id}).sort("created_at", 1)]
