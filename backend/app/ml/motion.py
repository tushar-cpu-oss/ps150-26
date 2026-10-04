"""OpenCV frame-differencing motion detection with event grouping (debouncing).

Continuous motion becomes ONE event per motion segment instead of one per frame.
"""
from typing import Dict, List, Optional

import cv2
import numpy as np


class MotionDetector:
    def __init__(self, pixel_threshold: int = 25, min_contour_area: int = 500, gap_seconds: float = 2.0):
        self.pixel_threshold = int(pixel_threshold)
        self.min_contour_area = int(min_contour_area)
        self.gap_seconds = float(gap_seconds)
        self._prev: Optional[np.ndarray] = None
        self._seg: Optional[Dict] = None

    def _score(self, frame: np.ndarray) -> float:
        """Return fraction (0..1) of the frame covered by moving regions >= min area."""
        h, w = frame.shape[:2]
        scale = 1.0
        if w > 640:
            scale = 640.0 / w
            frame = cv2.resize(frame, (640, int(h * scale)), interpolation=cv2.INTER_AREA)
        gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (21, 21), 0)
        if self._prev is None or self._prev.shape != gray.shape:
            self._prev = gray
            return 0.0
        diff = cv2.absdiff(self._prev, gray)
        self._prev = gray
        _, th = cv2.threshold(diff, self.pixel_threshold, 255, cv2.THRESH_BINARY)
        th = cv2.dilate(th, None, iterations=2)
        contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = self.min_contour_area * (scale ** 2)
        area = sum(cv2.contourArea(c) for c in contours if cv2.contourArea(c) >= min_area)
        return float(area) / float(gray.shape[0] * gray.shape[1])

    def _close(self) -> Dict:
        s = self._seg
        self._seg = None
        return {
            "frame_number": s["start_frame"],
            "video_time_seconds": s["start_t"],
            "motion_score": s["peak"],
            "metadata": {
                "end_video_time_seconds": s["last_t"],
                "duration_seconds": s["last_t"] - s["start_t"],
                "peak_frame_number": s["peak_frame"],
                "sampled_frames_with_motion": s["samples"],
            },
        }

    def process(self, frame: np.ndarray, frame_number: int, t: float) -> List[Dict]:
        """Feed one sampled frame; returns any motion events that just finished."""
        out: List[Dict] = []
        score = self._score(frame)
        if score > 0:
            if self._seg is not None and t - self._seg["last_t"] >= self.gap_seconds:
                out.append(self._close())  # motion resumed after a long pause: separate event
            if self._seg is None:
                self._seg = {"start_frame": frame_number, "start_t": t, "last_t": t,
                             "peak": score, "peak_frame": frame_number, "samples": 1}
            else:
                self._seg["last_t"] = t
                self._seg["samples"] += 1
                if score > self._seg["peak"]:
                    self._seg["peak"], self._seg["peak_frame"] = score, frame_number
        elif self._seg is not None and t - self._seg["last_t"] >= self.gap_seconds:
            out.append(self._close())
        return out

    def flush(self) -> List[Dict]:
        return [self._close()] if self._seg is not None else []
