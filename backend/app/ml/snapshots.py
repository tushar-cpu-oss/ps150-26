"""Annotated detection snapshots. These are analysis ARTIFACTS written to storage/snapshots/;
the original evidence file is never touched."""
import re
from pathlib import Path
from typing import Dict, List

import cv2

SNAPSHOT_RE = re.compile(r"^frame_\d{6,}\.jpg$")


def snapshot_name(frame_number: int) -> str:
    return f"frame_{frame_number:06d}.jpg"


def save_annotated_frame(frame, detections: List[Dict], t: float, dest_dir: Path, frame_number: int) -> str:
    """Draw bbox + class + confidence + timestamp on a COPY of the frame and write a JPEG."""
    img = frame.copy()
    for d in detections:
        b = d["bbox"]
        p1, p2 = (int(b["x1"]), int(b["y1"])), (int(b["x2"]), int(b["y2"]))
        cv2.rectangle(img, p1, p2, (0, 200, 0), 2)
        label = f'{d["class_name"]} {d["confidence"]:.2f}'
        (tw, th), base = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        y = max(p1[1], th + base + 2)
        cv2.rectangle(img, (p1[0], y - th - base - 2), (p1[0] + tw + 4, y), (0, 200, 0), -1)
        cv2.putText(img, label, (p1[0] + 2, y - base - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    stamp = f"t={t:.2f}s frame={frame_number}"
    cv2.putText(img, stamp, (8, img.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, stamp, (8, img.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = snapshot_name(frame_number)
    if not cv2.imwrite(str(dest_dir / name), img, [cv2.IMWRITE_JPEG_QUALITY, 85]):
        raise OSError("Could not write snapshot")
    return name
