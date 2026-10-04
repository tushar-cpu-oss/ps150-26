"""MongoDB access (PyMongo). Sync driver; endpoints are plain `def` so FastAPI runs
them in its threadpool. A 'mongomock://' URI is supported for tests only."""
import logging
import threading

from pymongo import ASCENDING, MongoClient, ReturnDocument

from app.config import get_settings

log = logging.getLogger(__name__)
_client = None
_lock = threading.Lock()

COLLECTIONS = ["users", "cases", "evidence", "devices", "analysis_jobs", "detections",
               "timeline_events", "chain_of_custody", "reports"]


def get_client():
    global _client
    with _lock:
        if _client is None:
            uri = get_settings().mongodb_uri
            if uri.startswith("mongomock://"):
                import mongomock
                _client = mongomock.MongoClient()
            else:
                _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        return _client


def reset_client() -> None:
    global _client
    with _lock:
        if _client is not None and hasattr(_client, "close"):
            try:
                _client.close()
            except Exception:
                pass
        _client = None


def get_db():
    return get_client()[get_settings().mongodb_database]


def init_indexes(db) -> None:
    db.users.create_index("email", unique=True)
    db.users.create_index("user_id", unique=True)
    db.cases.create_index("case_id", unique=True)
    db.evidence.create_index("evidence_id", unique=True)
    db.evidence.create_index("case_id")
    db.devices.create_index("case_id")
    db.devices.create_index("evidence_id")
    db.analysis_jobs.create_index("analysis_id", unique=True)
    db.analysis_jobs.create_index("evidence_id")
    db.detections.create_index("evidence_id")
    db.detections.create_index([("case_id", ASCENDING), ("class_name", ASCENDING)])
    db.timeline_events.create_index("evidence_id")
    db.timeline_events.create_index([("case_id", ASCENDING), ("timestamp", ASCENDING)])
    db.chain_of_custody.create_index("evidence_id")
    db.timeline_events.create_index("case_id")
    db.reports.create_index("report_id", unique=True)


def next_id(db, sequence: str, prefix: str, width: int) -> str:
    """Atomic sequential ID, e.g. next_id(db,'case','CASE-ROCKET',4) -> CASE-ROCKET-0001."""
    doc = db["counters"].find_one_and_update(
        {"_id": sequence}, {"$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER
    )
    return f"{prefix}-{doc['seq']:0{width}d}"


def ping(db) -> bool:
    try:
        db.command("ping")
        return True
    except Exception:
        return False
