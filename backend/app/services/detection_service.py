"""Builds detection + timeline documents from real model output."""
import uuid
from datetime import timedelta
from typing import Dict, List

from app.utils.timeutil import utcnow


def build_detection_docs(analysis: dict, evidence: dict, frame_number: int, t: float,
                         dets: List[Dict]) -> tuple[List[dict], List[dict]]:
    """Return (detection_docs, timeline_docs) for the detections found in one frame."""
    ts = evidence["recording_start"] + timedelta(seconds=t)
    now = utcnow()
    det_docs, tl_docs = [], []
    for d in dets:
        det_id = str(uuid.uuid4())
        det_docs.append({
            "detection_id": det_id, "analysis_id": analysis["analysis_id"],
            "case_id": analysis["case_id"], "evidence_id": evidence["evidence_id"],
            "timestamp": ts, "video_time_seconds": t, "frame_number": frame_number,
            "class_name": d["class_name"], "class_id": d.get("class_id"),
            "confidence": d["confidence"], "bbox": d["bbox"], "track_id": d.get("track_id"),
            "created_at": now,
        })
        tl_docs.append({
            "event_id": str(uuid.uuid4()), "case_id": analysis["case_id"],
            "evidence_id": evidence["evidence_id"], "analysis_id": analysis["analysis_id"],
            "timestamp": ts, "video_time_seconds": t, "event_type": "object_detection",
            "class_name": d["class_name"], "confidence": d["confidence"],
            "frame_number": frame_number, "camera_id": evidence.get("camera_id"),
            "motion_score": None, "detection_id": det_id,
            "metadata": {"bbox": d["bbox"], "class_id": d.get("class_id"), "track_id": d.get("track_id"), "timestamp_source": evidence.get("recording_start_source"), "timestamp_confidence": evidence.get("recording_start_confidence"), "timestamp_method": evidence.get("recording_start_method")},
        })
    return det_docs, tl_docs


def build_motion_timeline_doc(analysis: dict, evidence: dict, ev: Dict) -> dict:
    t = ev["video_time_seconds"]
    return {
        "event_id": str(uuid.uuid4()), "case_id": analysis["case_id"],
        "evidence_id": evidence["evidence_id"], "analysis_id": analysis["analysis_id"],
        "timestamp": evidence["recording_start"] + timedelta(seconds=t),
        "video_time_seconds": t, "event_type": "motion", "class_name": None, "confidence": None,
        "frame_number": ev["frame_number"], "camera_id": evidence.get("camera_id"),
        "motion_score": ev["motion_score"], "detection_id": None,
        "metadata": {**ev["metadata"], "timestamp_source": evidence.get("recording_start_source"), "timestamp_confidence": evidence.get("recording_start_confidence"), "timestamp_method": evidence.get("recording_start_method")},
    }
