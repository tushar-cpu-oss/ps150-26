"""Video analysis jobs: frame sampling -> motion detection + YOLO -> detections/timeline."""
import logging
import time
from typing import Optional

from app.config import get_settings
from app.database import get_db, next_id
from app.ml import detector as yolo
from app.ml.face import FaceDetector
from app.ml.motion import MotionDetector
from app.ml.snapshots import save_annotated_frame
from app.ml.video import VideoOpenError, iter_sampled_frames
from app.services import custody_service, decoder_service, detection_service, evidence_service, hashing_service, timeline_service
from app.utils.errors import AppError
from app.utils.files import VIDEO_EXTENSIONS
from app.utils.mongo import to_api
from app.utils.timeutil import utcnow

log = logging.getLogger(__name__)
BATCH = 200
PRESET_SAMPLE_RATES = {"fast": 1.0, "balanced": 2.0, "deep": 5.0}  # frames analysed per second


STAGE_ORDER = ["integrity_check", "decoding", "loading_models", "frame_analysis", "building_timeline", "finalizing"]


def _init_stages() -> list:
    return [{"name": n, "status": "pending"} for n in STAGE_ORDER]


def _stage(db, analysis_id: str, name: str, status: str = "running") -> None:
    """Record a REAL pipeline stage transition on the job (no estimated percentages).

    Marks `name` with `status`, sets job.stage to the active stage, and when a stage starts
    marks any earlier still-pending stage as skipped (e.g. decoding for a plain MP4)."""
    doc = db.analysis_jobs.find_one({"analysis_id": analysis_id}, {"stages": 1}) or {}
    stages = doc.get("stages") or _init_stages()
    idx = STAGE_ORDER.index(name)
    for i, st in enumerate(stages):
        if i < idx and st["status"] == "pending":
            st["status"] = "skipped"
        if st["name"] == name:
            st["status"] = status
    db.analysis_jobs.update_one({"analysis_id": analysis_id},
                                {"$set": {"stages": stages, "stage": name if status == "running" else None}})


def create_job(db, evidence_id: str, options: dict, actor: str) -> dict:
    s = get_settings()
    ev = evidence_service.get_evidence_doc(db, evidence_id)
    if ev["extension"] not in VIDEO_EXTENSIONS:
        raise AppError(400, "UNSUPPORTED_FOR_ANALYSIS", "Video analysis requires a video evidence file.")
    running = db.analysis_jobs.find_one({"evidence_id": evidence_id, "status": {"$in": ["queued", "processing"]}})
    if running:
        # Idempotent: tell the client WHICH job is running so it can attach instead of failing.
        raise AppError(409, "ANALYSIS_IN_PROGRESS", "An analysis is already running for this evidence.",
                       {"analysis_id": running["analysis_id"], "status": running["status"]})
    if not (options.get("object_detection") or options.get("motion_detection") or options.get("face_detection")):
        raise AppError(422, "NO_ANALYSIS_SELECTED", "Enable object_detection and/or motion_detection.")
    resolved = {
        "object_detection": bool(options.get("object_detection")),
        "motion_detection": bool(options.get("motion_detection")),
        "face_detection": bool(options.get("face_detection")),
        "object_tracking": bool(options.get("object_tracking")),
        "preset": options.get("preset"),
        "frame_sample_rate": (options.get("frame_sample_rate")
                              or PRESET_SAMPLE_RATES.get(options.get("preset") or "") or s.frame_sample_rate),
        "confidence_threshold": (options.get("confidence_threshold")
                                 if options.get("confidence_threshold") is not None
                                 else s.yolo_confidence_threshold),
        "motion_threshold": s.motion_threshold, "min_contour_area": s.min_contour_area,
        "yolo_model_path": str(s.yolo_model_file), "yolo_device": s.yolo_device,
        "yolo_classes": s.yolo_class_filter,
    }
    job = {
        "analysis_id": next_id(db, "analysis", "ANALYSIS-ROCKET", 6),
        "case_id": ev["case_id"], "evidence_id": evidence_id, "status": "queued",
        "options": resolved, "stage": None, "stages": _init_stages(), "model": None, "model_version": None, "progress": 0.0, "modules": {}, "warnings": [], "counts": {},
        "error": None, "requested_by": actor,
        "created_at": utcnow(), "started_at": None, "completed_at": None,
    }
    db.analysis_jobs.insert_one(dict(job))
    db.evidence.update_one({"evidence_id": evidence_id}, {"$set": {"analysis_status": "queued"}})
    return job


def get_job(db, analysis_id: str) -> dict:
    doc = db.analysis_jobs.find_one({"analysis_id": analysis_id})
    if not doc:
        raise AppError(404, "ANALYSIS_NOT_FOUND", "Analysis job was not found.")
    out = to_api(doc)
    out["options"] = {k: v for k, v in out["options"].items() if k != "yolo_model_path"}
    out.setdefault("snapshots", None)
    out["snapshots"] = len(doc.get("snapshots") or [])
    return out


def list_snapshots(db, analysis_id: str) -> list:
    doc = db.analysis_jobs.find_one({"analysis_id": analysis_id})
    if not doc:
        raise AppError(404, "ANALYSIS_NOT_FOUND", "Analysis job was not found.")
    return [{"frame_number": s["frame_number"], "timestamp": s["video_time_seconds"],
             "image_url": f"/api/analysis/{analysis_id}/snapshots/{s['filename']}",
             "detections": s["detections"]} for s in doc.get("snapshots") or []]


def _fail(db, job: dict, message: str, actor: str) -> None:
    log.error("Analysis %s failed: %s", job["analysis_id"], message)
    cur = db.analysis_jobs.find_one({"analysis_id": job["analysis_id"]}, {"stages": 1}) or {}
    stages = cur.get("stages") or []
    for st in stages:
        if st["status"] == "running":
            st["status"] = "failed"
    db.analysis_jobs.update_one({"analysis_id": job["analysis_id"]},
                                {"$set": {"status": "failed", "error": message, "completed_at": utcnow(),
                                          "stages": stages, "stage": None}})
    db.evidence.update_one({"evidence_id": job["evidence_id"]}, {"$set": {"analysis_status": "failed"}})


def run_job(analysis_id: str, actor: str = "system") -> None:
    """Executed in the background. Never raises; failures are recorded on the job."""
    db = get_db()
    job = db.analysis_jobs.find_one({"analysis_id": analysis_id})
    if not job:
        return
    try:
        _run(db, job, actor)
    except Exception as e:  # noqa: BLE001
        log.exception("Unexpected analysis error")
        _fail(db, job, f"Unexpected error: {type(e).__name__}", actor)


def _run(db, job: dict, actor: str) -> None:
    opts = job["options"]
    ev = evidence_service.get_evidence_doc(db, job["evidence_id"])
    path = evidence_service.resolve_path(ev)
    db.analysis_jobs.update_one({"analysis_id": job["analysis_id"]},
                                {"$set": {"status": "processing", "started_at": utcnow()}})
    db.evidence.update_one({"evidence_id": ev["evidence_id"]}, {"$set": {"analysis_status": "processing"}})
    custody_service.record(db, ev["case_id"], ev["evidence_id"], "ANALYSIS_STARTED", actor, ev["sha256"],
                           f"Analysis {job['analysis_id']} started (read-only access to original evidence).")
    timeline_service.add_system_event(db, ev["case_id"], ev["evidence_id"], "ANALYSIS_STARTED", utcnow(),
                                      f"Analysis {job['analysis_id']} started", source="analysis",
                                      camera_id=ev.get("camera_id"), extra={"analysis_id": job["analysis_id"]})

    # Integrity gate: never analyse a file that no longer matches its acquisition hash.
    _stage(db, job["analysis_id"], "integrity_check")
    if not path.exists() or hashing_service.hash_file(path)["sha256"] != ev["sha256"]:
        return _fail(db, job, "Evidence integrity check failed; analysis aborted.", actor)

    modules, warnings = {}, []
    analysis_path = path
    _stage(db, job["analysis_id"], "integrity_check", "completed")
    if path.suffix.lower().lstrip(".") in {"dav", "ifv", "h264", "264", "h265", "hevc", "ts", "mts", "m2ts", "webm"}:
        _stage(db, job["analysis_id"], "decoding")
        try:
            working = get_settings().processed_dir / "decoded" / job["analysis_id"] / "analysis.mp4"
            analysis_path = decoder_service.decode_to_mp4(path, working)
            modules["format_decoder"] = "completed"
            _stage(db, job["analysis_id"], "decoding", "completed")
        except AppError as e:
            modules["format_decoder"] = "failed"
            warnings.append(str(e))
            return _fail(db, job, "CCTV/raw video decoding failed before analysis: " + e.message, actor)
    _stage(db, job["analysis_id"], "loading_models")
    detector: Optional[yolo.YoloDetector] = None
    if opts["object_detection"]:
        try:
            detector = yolo.get_detector(opts["yolo_model_path"], opts.get("yolo_device", "cpu"),
                                         opts.get("yolo_classes"), tracking=opts.get("object_tracking", False))
            modules["object_detection"] = "completed"
            db.analysis_jobs.update_one({"analysis_id": job["analysis_id"]}, {"$set": {
                "model": detector.model_name, "model_version": detector.model_version}})
        except yolo.DetectorUnavailable as e:
            modules["object_detection"] = "unavailable"
            warnings.append(f"ML_MODEL_UNAVAILABLE - object detection skipped: {e}")
    else:
        modules["object_detection"] = "disabled"
    motion = None
    face = None
    if opts["face_detection"]:
        try:
            face = FaceDetector()
            modules["face_detection"] = "completed"
        except Exception as e:
            modules["face_detection"] = "unavailable"
            warnings.append(f"FACE_DETECTOR_UNAVAILABLE - face detection skipped: {e}")
    else:
        modules["face_detection"] = "disabled"
    if opts["motion_detection"]:
        s = get_settings()
        motion = MotionDetector(opts["motion_threshold"], opts["min_contour_area"], s.motion_gap_seconds)
        modules["motion_detection"] = "completed"
    else:
        modules["motion_detection"] = "disabled"
    if detector is None and motion is None and face is None:
        return _fail(db, job, "No analysis module could run. " + " ".join(warnings), actor)

    _stage(db, job["analysis_id"], "loading_models", "completed")
    _stage(db, job["analysis_id"], "frame_analysis")
    counts = {"frames_analysed": 0, "detections": 0, "face_detections": 0, "motion_events": 0, "track_detections": 0, "unique_track_ids": 0}
    track_ids = set()
    det_buf, tl_buf = [], []
    snapshots = []
    snap_dir = get_settings().snapshots_dir / job["analysis_id"]
    max_snaps = get_settings().max_snapshots_per_analysis

    def flush():
        if det_buf:
            db.detections.insert_many(list(det_buf))
        if tl_buf:
            db.timeline_events.insert_many(list(tl_buf))
        det_buf.clear(); tl_buf.clear()

    last_progress = 0.0
    try:
        for frame_no, t, frame, info in iter_sampled_frames(analysis_path, opts["frame_sample_rate"]):
            counts["frames_analysed"] += 1
            if motion is not None:
                for m in motion.process(frame, frame_no, t):
                    tl_buf.append(detection_service.build_motion_timeline_doc(job, ev, m))
                    counts["motion_events"] += 1
            if face is not None:
                face_dets = face.detect(frame)
                for fd in face_dets:
                    face_id = str(__import__("uuid").uuid4())
                    ts = ev["recording_start"] + __import__("datetime").timedelta(seconds=t)
                    tl_buf.append({"event_id": face_id, "case_id": job["case_id"], "evidence_id": ev["evidence_id"],
                                   "analysis_id": job["analysis_id"], "timestamp": ts, "video_time_seconds": t,
                                   "event_type": "face_detection", "class_name": "face", "confidence": None,
                                   "frame_number": frame_no, "camera_id": ev.get("camera_id"), "motion_score": None,
                                   "detection_id": None, "metadata": {"bbox": fd["bbox"], "identity": "NOT_PERFORMED",
                                   "timestamp_source": ev.get("recording_start_source")}})
                    counts["face_detections"] += 1
            if detector is not None:
                dets = detector.track(frame, opts["confidence_threshold"]) if opts.get("object_tracking") else detector.detect(frame, opts["confidence_threshold"])
                for d in dets:
                    if d.get("track_id") is not None:
                        track_ids.add(int(d["track_id"]))
                        counts["track_detections"] += 1
                counts["unique_track_ids"] = len(track_ids)
                d_docs, t_docs = detection_service.build_detection_docs(job, ev, frame_no, t, dets)
                det_buf.extend(d_docs); tl_buf.extend(t_docs)
                counts["detections"] += len(d_docs)
                if dets and len(snapshots) < max_snaps:
                    try:
                        name = save_annotated_frame(frame, dets, t, snap_dir, frame_no)
                        snapshots.append({"frame_number": frame_no, "video_time_seconds": t, "filename": name,
                                          "detections": [{"class": d["class_name"], "class_id": d.get("class_id"),
                                                          "confidence": d["confidence"],
                                                          "track_id": d.get("track_id"),
                                                          "bbox": [d["bbox"]["x1"], d["bbox"]["y1"],
                                                                   d["bbox"]["x2"], d["bbox"]["y2"]]} for d in dets]})
                    except Exception as e:  # noqa: BLE001 - a snapshot failure must not fail the analysis
                        log.warning("Snapshot failed for frame %s: %s", frame_no, e)
            if len(det_buf) + len(tl_buf) >= BATCH:
                flush()
            if info.frame_count and time.monotonic() - last_progress > 1.0:
                last_progress = time.monotonic()
                db.analysis_jobs.update_one({"analysis_id": job["analysis_id"]},
                                            {"$set": {"progress": min(0.99, frame_no / info.frame_count)}})
        _stage(db, job["analysis_id"], "frame_analysis", "completed")
        _stage(db, job["analysis_id"], "building_timeline")
        if motion is not None:
            for m in motion.flush():
                tl_buf.append(detection_service.build_motion_timeline_doc(job, ev, m))
                counts["motion_events"] += 1
        flush()
        _stage(db, job["analysis_id"], "building_timeline", "completed")
        _stage(db, job["analysis_id"], "finalizing")
    except VideoOpenError as e:
        flush()
        return _fail(db, job, str(e), actor)

    if opts.get("object_tracking") and detector is not None:
        modules["object_tracking"] = "completed"
    else:
        modules["object_tracking"] = "disabled"
    db.analysis_jobs.update_one({"analysis_id": job["analysis_id"]}, {"$set": {
        "snapshots": snapshots, "status": "completed", "progress": 1.0, "modules": modules, "warnings": warnings,
        "counts": counts, "completed_at": utcnow(), "stage": None}})
    _stage(db, job["analysis_id"], "finalizing", "completed")
    db.analysis_jobs.update_one({"analysis_id": job["analysis_id"]}, {"$set": {"stage": None}})
    db.evidence.update_one({"evidence_id": ev["evidence_id"]},
                           {"$set": {"analysis_status": "completed", "latest_analysis_id": job["analysis_id"]}})
    timeline_service.add_system_event(db, ev["case_id"], ev["evidence_id"], "ANALYSIS_COMPLETED", utcnow(),
                                      f"Analysis {job['analysis_id']} completed", source="analysis",
                                      camera_id=ev.get("camera_id"),
                                      extra={"analysis_id": job["analysis_id"], "counts": counts})
    custody_service.record(db, ev["case_id"], ev["evidence_id"], "ANALYSIS_COMPLETED", actor, ev["sha256"],
                           f"Analysis {job['analysis_id']} completed. counts={counts} modules={modules}")
