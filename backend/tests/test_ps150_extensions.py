"""Dependency-light tests for the final PS-150 extension modules."""
from pathlib import Path
import tempfile
import cv2
import numpy as np

from app.ml.face import FaceDetector
from app.services.decoder_service import ffmpeg_available
from app.services.recovery_service import carve_standard_video
from app.services.vendor_adapters import normalize, support_matrix


def test_cctv_adapters_and_ffmpeg():
    assert support_matrix()["CCTV container (FFmpeg)"] == "SUPPORTED"
    n = normalize("camera.dav")
    assert n.source_format == "dav"
    assert n.capabilities["format_decoder"] == "SUPPORTED_VIA_FFMPEG"
    assert ffmpeg_available()


def test_face_detector_loads():
    detector = FaceDetector()
    assert detector.cascade.empty() is False
    frame = np.zeros((128, 128, 3), dtype=np.uint8)
    assert detector.detect(frame) == []


def test_standard_signature_carving():
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "raw.dd"
        out = Path(td) / "recovered"
        ok, encoded = cv2.imencode(".png", np.zeros((4, 4, 3), dtype=np.uint8))
        assert ok
        src.write_bytes(b"A" * 4096 + encoded.tobytes() + b"B" * 4096)
        recovered = carve_standard_video(src, out)
        assert len(recovered) == 1
        assert recovered[0]["extension"] == "png"
        assert Path(recovered[0]["artifact"]).read_bytes() == encoded.tobytes()
