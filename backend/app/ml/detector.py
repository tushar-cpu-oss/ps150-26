"""Ultralytics YOLO wrapper. Only real model output is returned - nothing is invented.

Model weights are NOT shipped in the repo. See models/README.txt and scripts/download_model.py.
"""
import logging
import os
import threading
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


class DetectorUnavailable(RuntimeError):
    """Raised when YOLO cannot be used (package/weights missing). API code: ML_MODEL_UNAVAILABLE."""


def model_status(model_file: str, device: str) -> Dict:
    """Cheap availability probe for /health (does NOT load the model)."""
    info = {"ML_MODEL_AVAILABLE": False, "MODEL_NAME": os.path.basename(str(model_file)),
            "MODEL_VERSION": None, "DEVICE": device, "weights_path": str(model_file),
            "weights_present": os.path.exists(str(model_file)), "ultralytics_installed": False, "reason": None}
    try:
        import ultralytics
        info["ultralytics_installed"] = True
        info["MODEL_VERSION"] = f"ultralytics {ultralytics.__version__}"
    except Exception as e:  # noqa: BLE001
        info["reason"] = f"ultralytics is not importable: {e}"
        return info
    if not info["weights_present"]:
        info["reason"] = (f"Weights file not found at {model_file}. "
                          "Run: python scripts/download_model.py (see models/README.txt).")
        return info
    info["ML_MODEL_AVAILABLE"] = True
    return info


class YoloDetector:
    def __init__(self, model_path: str, device: str = "cpu", class_filter: Optional[List[str]] = None):
        if not os.path.exists(model_path):
            raise DetectorUnavailable(
                f"ML_MODEL_UNAVAILABLE: weights not found at '{model_path}'. "
                "Run `python scripts/download_model.py` or see models/README.txt.")
        try:
            import ultralytics
            from ultralytics import YOLO
        except Exception as e:  # ImportError or torch failures
            raise DetectorUnavailable(f"ML_MODEL_UNAVAILABLE: ultralytics is not usable: {e}") from e
        try:
            self.model = YOLO(model_path)
        except Exception as e:
            raise DetectorUnavailable(f"ML_MODEL_UNAVAILABLE: model '{model_path}' could not be loaded: {e}") from e
        self.model_path = model_path
        self.model_name = os.path.basename(model_path)
        self.model_version = f"ultralytics {ultralytics.__version__}"
        self.device = device
        self.names: Dict[int, str] = dict(self.model.names)
        self.class_filter = set(class_filter or [])
        self._lock = threading.Lock()

    def track(self, frame, confidence: float) -> List[Dict]:
        """Run real Ultralytics ByteTrack tracking and return video-local track IDs.

        Track IDs are not identities. The tracker is intentionally opt-in because it
        adds compute and maintains temporal state across frames.
        """
        with self._lock:
            result = self.model.track(
                frame, conf=confidence, device=self.device, verbose=False,
                persist=True, tracker="bytetrack.yaml"
            )[0]
        out = []
        ids = result.boxes.id
        for i, box in enumerate(result.boxes):
            class_id = int(box.cls[0])
            name = self.names.get(class_id)
            if self.class_filter and name not in self.class_filter:
                continue
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
            track_id = int(ids[i]) if ids is not None else None
            out.append({
                "class_name": name, "class_id": class_id, "confidence": float(box.conf[0]),
                "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                "track_id": track_id,
            })
        return out

    def detect(self, frame, confidence: float) -> List[Dict]:
        with self._lock:
            result = self.model.predict(frame, conf=confidence, device=self.device, verbose=False)[0]
        out = []
        for box in result.boxes:
            class_id = int(box.cls[0])
            name = self.names.get(class_id)
            if self.class_filter and name not in self.class_filter:
                continue
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
            out.append({"class_name": name, "class_id": class_id, "confidence": float(box.conf[0]),
                        "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}})
        return out


_cache: Dict[tuple, YoloDetector] = {}
_cache_lock = threading.Lock()


def get_detector(model_path: str, device: str = "cpu", class_filter: Optional[List[str]] = None, tracking: bool = False) -> YoloDetector:
    """Return a detector. Tracking sessions are deliberately not cached so tracker state
    can never leak between independent evidence analyses."""
    if tracking:
        return YoloDetector(model_path, device, class_filter)
    key = (model_path, device, tuple(sorted(class_filter or [])))
    with _cache_lock:
        if key not in _cache:
            _cache[key] = YoloDetector(model_path, device, class_filter)
        return _cache[key]
