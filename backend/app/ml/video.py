"""Frame sampling with OpenCV. Never loads the whole video into memory."""
from dataclasses import dataclass
from typing import Iterator, Tuple

import cv2
import numpy as np


class VideoOpenError(RuntimeError):
    pass


@dataclass
class VideoInfo:
    fps: float
    frame_count: int
    width: int
    height: int


def open_video(path) -> Tuple[cv2.VideoCapture, VideoInfo]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise VideoOpenError("OpenCV could not open the video file.")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps <= 0 or fps > 1000:
        cap.release()
        raise VideoOpenError("Video reports an invalid frame rate; cannot compute timestamps.")
    info = VideoInfo(
        fps=fps,
        frame_count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0),
        width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0),
        height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0),
    )
    return cap, info


def iter_sampled_frames(path, sample_rate: float) -> Iterator[Tuple[int, float, np.ndarray, VideoInfo]]:
    """Yield (frame_number, seconds_from_start, frame_bgr, info) at ~sample_rate frames/sec.

    frame_number is the 0-based index in the video, so a player can seek to
    frame_number / fps. Non-sampled frames are grabbed (decoded) but not converted.
    """
    if sample_rate <= 0:
        raise ValueError("sample_rate must be > 0")
    cap, info = open_video(path)
    step = max(1, int(round(info.fps / sample_rate)))
    idx = 0
    try:
        while True:
            if not cap.grab():
                break
            if idx % step == 0:
                ok, frame = cap.retrieve()
                if not ok:
                    break
                yield idx, idx / info.fps, frame, info
            idx += 1
    finally:
        cap.release()
