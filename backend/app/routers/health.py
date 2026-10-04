import os
import shutil

from fastapi import APIRouter, Depends

from app.config import get_settings
from app.database import get_db, ping

router = APIRouter(tags=["system"])

CAPABILITIES = {
    "implemented": [
        "Case management", "Evidence upload with validation", "Real SHA-256 / MD5 hashing and re-verification",
        "FFprobe metadata extraction", "Metadata-keyword device inference + manual device entry",
        "OpenCV motion detection with event grouping", "YOLO general object detection (requires model)",
        "Unified timeline + structured search", "Cross-camera TEMPORAL correlation (not identity)",
        "JWT authentication (Argon2/scrypt passwords)", "Range-enabled video streaming", "Annotated detection snapshots",
        "Chain of custody (actor from JWT)", "PDF report generation",
        "CCTV DAV/IFV decoding through FFmpeg", "Raw-video stream decoding",
        "Read-only forensic image ingestion + hashing", "Standard-signature file carving",
        "OpenCV face detection (detection only)"],
    "prototype_or_simulated": [
        "Evidence 'acquisition' = file upload of exported footage (no device connection)",
        "Vendor identification is a low-confidence text match on metadata, not a forensic determination",
        "Absolute event times depend on the recording_start source recorded per evidence"],
    "future": [
        "Proprietary DVR/NVR filesystem parsing", "OEM deleted-record reconstruction",
        "Vendor-specific acquisition protocols", "Natural-language AI search", "Fine-grained RBAC / per-evidence ownership checks", "Face recognition / person re-identification"],
}


@router.get("/health")
def health(db=Depends(get_db)):
    from app.ml.detector import model_status
    s = get_settings()
    try:
        import cv2
        opencv = True
    except Exception:
        opencv = False
    ml = model_status(str(s.yolo_model_file), s.yolo_device)
    db_up = ping(db)
    ffprobe = shutil.which("ffprobe") is not None
    return {
        "status": "ok" if (db_up and ffprobe and opencv) else "degraded",
        "product": "ROCKET FORENSICS", "team": "TEAM ROCKET", "version": s.app_version,
        "database": "connected" if db_up else "disconnected",
        "ffprobe": ffprobe, "opencv": opencv, "ml_model": ml["ML_MODEL_AVAILABLE"],
        "ml": ml,
        "dependencies": {
            "mongodb": "up" if db_up else "down", "ffprobe": ffprobe,
            "ultralytics_installed": ml["ultralytics_installed"],
            "yolo_model_file_present": ml["weights_present"],
        },
        "capabilities": CAPABILITIES,
    }
