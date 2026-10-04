YOLO weights go here (NOT committed to git).

Download:   python scripts/download_model.py          # fetches yolo11n.pt (needs internet)
Configure:  YOLO_MODEL_PATH=models/yolo11n.pt, YOLO_CONFIDENCE=0.35, YOLO_DEVICE=cpu   (in .env)
Test:       GET /health  -> "ml_model": true and ml.ML_MODEL_AVAILABLE: true
            pytest tests/test_real_yolo.py   (skipped automatically if weights/ultralytics are missing)

If weights are missing, analysis reports ML_MODEL_UNAVAILABLE and only motion detection runs.
No detections are ever invented.
