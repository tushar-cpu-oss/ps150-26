"""Test helpers: build real video files with OpenCV (no mocks of file contents)."""
from pathlib import Path

import cv2
import numpy as np


def make_video(path: Path, seconds: int = 10, fps: int = 10, size=(320, 240),
               motion_windows=((3, 5), (7, 8))) -> Path:
    """MJPG .avi with a white square moving during motion_windows and static black otherwise."""
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, size)
    for i in range(seconds * fps):
        t = i / fps
        frame = np.zeros((size[1], size[0], 3), np.uint8)
        if any(a <= t < b for a, b in motion_windows):
            x = int((t * 60) % 200)
            cv2.rectangle(frame, (x, 80), (x + 60, 140), (255, 255, 255), -1)
        w.write(frame)
    w.release()
    return path
