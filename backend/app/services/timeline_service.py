"""Unified chronological timeline + structured search."""
import uuid
from datetime import timedelta
from typing import List, Optional

from app.services import case_service
from app.utils.errors import AppError
from app.utils.mongo import to_api
from app.utils.timeutil import parse_time_filter, time_of_day_in_range

HARD_LIMIT = 20000


def _parse(value: Optional[str], name: str):
    if value is None or value == "":
        return None
    try:
        return parse_time_filter(value)
    except ValueError as e:
        raise AppError(422, "INVALID_TIME_FILTER", f"{name}: {e}")


def query_events(db, case_id: str, start_time: Optional[str] = None, end_time: Optional[str] = None,
                 event_type: Optional[str] = None, camera_id: Optional[str] = None,
                 min_confidence: Optional[float] = None, evidence_id: Optional[str] = None,
                 analysis_id: Optional[str] = None, class_name: Optional[str] = None,
                 limit: int = 1000) -> List[dict]:
    case_service.get_case_doc(db, case_id)
    q: dict = {"case_id": case_id}

    # By default show results of the latest completed analysis per evidence, so re-running
    # an analysis does not double-count. Events with no analysis (future device events) always show.
    if analysis_id:
        q["analysis_id"] = analysis_id
    else:
        ev_q = {"case_id": case_id, "latest_analysis_id": {"$ne": None}}
        if evidence_id:
            ev_q["evidence_id"] = evidence_id
        latest = [e["latest_analysis_id"] for e in db.evidence.find(ev_q)]
        q["$or"] = [{"analysis_id": {"$in": latest}}, {"analysis_id": None}]
    if evidence_id:
        q["evidence_id"] = evidence_id
    if event_type:
        q["event_type"] = event_type
    if camera_id:
        q["camera_id"] = camera_id
    if class_name:
        q["class_name"] = class_name
    if min_confidence is not None:
        q["confidence"] = {"$gte": float(min_confidence)}

    start, end = _parse(start_time, "start_time"), _parse(end_time, "end_time")
    tod_start = tod_end = None
    ts_q = {}
    for parsed, op in ((start, "$gte"), (end, "$lte")):
        if parsed is None:
            continue
        if parsed[0] == "datetime":
            ts_q[op] = parsed[1]
        elif op == "$gte":
            tod_start = parsed[1]
        else:
            tod_end = parsed[1]
    if ts_q:
        q["timestamp"] = ts_q

    cur = db.timeline_events.find(q).sort([("timestamp", 1), ("frame_number", 1)]).limit(HARD_LIMIT)
    out = []
    for d in cur:
        if (tod_start or tod_end) and not time_of_day_in_range(d["timestamp"].time(), tod_start, tod_end):
            continue
        out.append(to_api(d))
        if len(out) >= limit:
            break
    return out


def search(db, req: dict) -> List[dict]:
    obj = (req.get("object_type") or "").strip().lower() or None
    return query_events(
        db, req["case_id"], start_time=req.get("start_time"), end_time=req.get("end_time"),
        event_type="motion" if obj == "motion" else ("object_detection" if obj else None),
        camera_id=req.get("camera_id"), min_confidence=req.get("minimum_confidence"),
        evidence_id=req.get("evidence_id"),
        class_name=None if obj in (None, "motion") else obj, limit=req.get("limit", 500))


def add_system_event(db, case_id: str, evidence_id: str, event_type: str, timestamp, description: str,
                     video_time_seconds: Optional[float] = None, source: str = "system",
                     camera_id: Optional[str] = None, extra: Optional[dict] = None) -> dict:
    """Record a non-detection timeline event (VIDEO_START, ANALYSIS_COMPLETED, ...). analysis_id is
    None so these are always visible regardless of which analysis run is 'latest'."""
    doc = {"event_id": str(uuid.uuid4()), "case_id": case_id, "evidence_id": evidence_id, "analysis_id": None,
           "timestamp": timestamp, "video_time_seconds": video_time_seconds, "event_type": event_type,
           "class_name": None, "confidence": None, "frame_number": None, "camera_id": camera_id,
           "motion_score": None, "detection_id": None,
           "metadata": {"description": description, "source": source, **(extra or {})}}
    db.timeline_events.insert_one(dict(doc))
    return doc


CORRELATION_DISCLAIMER = ("Temporally correlated events only. This does NOT establish that the same person or "
                          "vehicle appears on multiple cameras: no identity or re-identification model is used.")


def correlate(events: List[dict], window_seconds: float = 30.0, class_name: Optional[str] = None) -> List[dict]:
    """Group object_detection events of the same class that occur on DIFFERENT cameras within
    `window_seconds` of each other (chained: each event within the window of the previous one)."""
    by_class = {}
    for e in events:
        if e.get("event_type") != "object_detection" or not e.get("camera_id") or not e.get("class_name"):
            continue
        if class_name and e["class_name"] != class_name:
            continue
        by_class.setdefault(e["class_name"], []).append(e)
    groups = []
    for cls, evs in by_class.items():
        evs.sort(key=lambda x: x["timestamp"])
        cluster = [evs[0]]
        for e in evs[1:] + [None]:
            if e is not None and (e["timestamp"] - cluster[-1]["timestamp"]).total_seconds() <= window_seconds:
                cluster.append(e)
                continue
            cams = sorted({c["camera_id"] for c in cluster})
            if len(cams) >= 2:
                groups.append({
                    "group_id": f"CORR-{len(groups) + 1:04d}", "class_name": cls, "cameras": cams,
                    "start_time": cluster[0]["timestamp"], "end_time": cluster[-1]["timestamp"],
                    "window_seconds": window_seconds, "event_count": len(cluster),
                    "label": "temporally correlated event",
                    "events": [{"event_id": c["event_id"], "camera_id": c["camera_id"], "timestamp": c["timestamp"],
                                "evidence_id": c["evidence_id"], "video_time_seconds": c.get("video_time_seconds"),
                                "confidence": c.get("confidence")} for c in cluster]})
            if e is not None:
                cluster = [e]
    groups.sort(key=lambda g: g["start_time"])
    return groups
