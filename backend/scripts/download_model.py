#!/usr/bin/env python3
"""Download YOLO weights into ./models (needs internet + `pip install ultralytics`).

    python scripts/download_model.py                # yolo11n.pt (default)
    python scripts/download_model.py yolov8n.pt

Then set YOLO_MODEL_PATH=models/<name> in .env. Verify with GET /health -> ml_model: true.
"""
import shutil
import sys
from pathlib import Path

name = sys.argv[1] if len(sys.argv) > 1 else "yolo11n.pt"
dest = Path(__file__).resolve().parents[1] / "models" / name
dest.parent.mkdir(exist_ok=True)
if dest.exists():
    print(f"Already present: {dest}")
    sys.exit(0)
try:
    from ultralytics import YOLO
except ImportError:
    sys.exit("ultralytics is not installed. Run: pip install -r requirements.txt")
YOLO(name)  # ultralytics downloads the official weights to the current directory if absent
cwd_copy = Path.cwd() / name
if cwd_copy.exists():
    shutil.move(str(cwd_copy), dest)
print(f"Weights ready at {dest}" if dest.exists() else
      "Download failed. Download manually from https://github.com/ultralytics/assets/releases and place in models/.")
