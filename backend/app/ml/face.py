"""Actual face detection using OpenCV's bundled Haar cascade.

This is detection only. It does not identify a person, perform biometric matching, or infer identity.
"""
from pathlib import Path
from typing import Dict, List
import cv2


class FaceDetector:
    def __init__(self, scale_factor: float = 1.1, min_neighbors: int = 5):
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        if not cascade_path.exists():
            raise RuntimeError("OpenCV Haar cascade is unavailable")
        self.cascade = cv2.CascadeClassifier(str(cascade_path))
        if self.cascade.empty():
            raise RuntimeError("OpenCV face cascade failed to load")
        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors

    def detect(self, frame) -> List[Dict]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.cascade.detectMultiScale(gray, scaleFactor=self.scale_factor,
                                               minNeighbors=self.min_neighbors, minSize=(24, 24))
        out = []
        for x, y, w, h in faces:
            out.append({"class_name": "face", "class_id": None, "confidence": None,
                        "bbox": {"x1": float(x), "y1": float(y),
                                  "x2": float(x + w), "y2": float(y + h)}})
        return out
