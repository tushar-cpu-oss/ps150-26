"""Tests for framework-independent modules (hashing, metadata, motion, validation, PDF).
These need no MongoDB/FastAPI."""
import hashlib
from datetime import datetime, time, timedelta

import pytest

from app.ml.motion import MotionDetector
from app.ml.video import iter_sampled_frames
from app.services import hashing_service, metadata_service, report_service
from app.services.device_inference import infer_from_metadata
from app.utils import files
from app.utils.errors import AppError
from app.utils.timeutil import parse_time_filter, time_of_day_in_range
from tests.helpers import make_video


def test_sha256_and_md5_match_independent_calculation(tmp_path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"rocket" * 500_000)  # ~3 MB, spans multiple chunks
    h = hashing_service.hash_file(p)
    assert h["sha256"] == hashlib.sha256(p.read_bytes()).hexdigest()
    assert h["md5"] == hashlib.md5(p.read_bytes()).hexdigest()


def test_hash_changes_when_file_modified(tmp_path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"original")
    before = hashing_service.hash_file(p)
    p.write_bytes(b"originaL")
    assert hashing_service.hash_file(p)["sha256"] != before["sha256"]


def test_video_metadata_is_real(tmp_path):
    p = make_video(tmp_path / "v.avi", seconds=10, fps=10, size=(320, 240))
    m = metadata_service.extract_metadata(p, "v.avi")
    assert (m["width"], m["height"]) == (320, 240)
    assert m["fps"] == pytest.approx(10.0)
    assert m["duration"] == pytest.approx(10.0, abs=0.2)
    assert m["frame_count"] == 100
    assert m["codec"] == "mjpeg"
    assert m["video_streams"] == 1 and m["audio_streams"] == 0


def test_motion_events_are_grouped_not_duplicated(tmp_path):
    p = make_video(tmp_path / "v.avi", motion_windows=((3, 5), (7, 8)))
    det, events = MotionDetector(25, 500, gap_seconds=1.0), []
    for frame_no, t, frame, _ in iter_sampled_frames(p, 2):
        events += det.process(frame, frame_no, t)
    events += det.flush()
    assert len(events) == 2                       # two motion segments -> two events
    assert 2.5 <= events[0]["video_time_seconds"] <= 3.6
    assert 6.5 <= events[1]["video_time_seconds"] <= 7.6
    assert all(0 < e["motion_score"] <= 1 for e in events)
    assert events[0]["frame_number"] == round(events[0]["video_time_seconds"] * 10)


def test_static_video_has_no_motion(tmp_path):
    p = make_video(tmp_path / "s.avi", motion_windows=())
    det, events = MotionDetector(), []
    for frame_no, t, frame, _ in iter_sampled_frames(p, 2):
        events += det.process(frame, frame_no, t)
    assert events + det.flush() == []


def test_frame_sampling_rate(tmp_path):
    p = make_video(tmp_path / "v.avi", seconds=10, fps=10)
    frames = list(iter_sampled_frames(p, 2))
    assert len(frames) == 20 and frames[1][0] == 5  # every 5th frame at 10fps -> 2 fps


def test_filename_sanitising_and_extension_validation():
    assert files.sanitize_filename("../../etc/passwd.mp4") == "passwd.mp4"
    assert files.sanitize_filename("..\\..\\evil.exe") == "evil.exe"
    with pytest.raises(AppError) as e:
        files.get_extension("evil.exe")
    assert e.value.status_code == 415
    with pytest.raises(AppError):
        files.validate_declared_mime("mp4", "text/html")


def test_magic_bytes_reject_renamed_file(tmp_path):
    import io
    with pytest.raises(AppError) as e:
        files.copy_with_limit(io.BytesIO(b"MZ\x90\x00" + b"\0" * 100), tmp_path / "a.mp4", 10_000, "mp4")
    assert e.value.code == "CONTENT_MISMATCH" and not (tmp_path / "a.mp4").exists()


def test_size_limit_enforced_and_partial_file_removed(tmp_path):
    import io
    data = b"RIFF\0\0\0\0AVI " + b"\0" * 5000
    with pytest.raises(AppError) as e:
        files.copy_with_limit(io.BytesIO(data), tmp_path / "a.avi", 1000, "avi")
    assert e.value.status_code == 413 and not (tmp_path / "a.avi").exists()


def test_safe_join_blocks_traversal(tmp_path):
    with pytest.raises(AppError):
        files.safe_join(tmp_path, "../outside.txt")


def test_time_filters():
    assert parse_time_filter("22:00:00") == ("time", time(22, 0))
    assert parse_time_filter("2026-01-05T22:00:00Z")[0] == "datetime"
    with pytest.raises(ValueError):
        parse_time_filter("not a time")
    assert time_of_day_in_range(time(22, 30), time(22), time(23))
    assert not time_of_day_in_range(time(21, 59), time(22), time(23))
    assert time_of_day_in_range(time(1), time(22), time(2))  # crosses midnight


def test_device_inference_never_guesses_vendor():
    r = infer_from_metadata({"tags": {"encoder": "Lavf60"}}, "clip.avi")
    assert r["manufacturer"] == "Unknown" and r["confidence"] is None and r["identification_method"] == "insufficient_evidence"
    assert "could not be determined" in r["confidence_basis"]
    r = infer_from_metadata({"tags": {"comment": "Recorded by Hikvision DS-7208"}}, "clip.avi")
    assert r["manufacturer"] == "Hikvision" and r["confidence"] == "low"
    # whole-word matching keeps false positives low
    assert infer_from_metadata({}, "the_matrix_movie.avi")["manufacturer"] == "Unknown"
    assert infer_from_metadata({"tags": {"title": "Matrix DVR ch1"}}, "a.avi")["manufacturer"] == "Matrix"


def test_pdf_report_renders(tmp_path):
    now = datetime(2026, 1, 5, 22, 0, 0)
    ev = {"evidence_id": "EV-ROCKET-000001", "case_id": "CASE-ROCKET-0001", "original_filename": "a.avi",
          "file_size": 10, "mime_type": "video/x-msvideo", "camera_id": None, "created_at": now,
          "uploaded_by": "tester", "recording_start": now, "recording_start_source": "investigator_supplied",
          "analysis_status": "completed", "sha256": "a" * 64, "md5": "b" * 32, "hashed_at": now,
          "last_verification_passed": None, "last_verified_at": None,
          "metadata": {"format": "avi", "duration": 10.0}, "metadata_error": None}
    events = [{"event_type": "object_detection", "class_name": "person", "confidence": 0.9,
               "timestamp": now, "video_time_seconds": 1.0, "frame_number": 10},
              {"event_type": "motion", "class_name": None, "confidence": None,
               "timestamp": now + timedelta(seconds=3), "video_time_seconds": 3.0, "frame_number": 30}]
    ctx = {"case": {"case_id": "CASE-ROCKET-0001", "name": "n", "description": "d", "investigator": "i",
                    "status": "active", "created_at": now},
           "evidence_items": [{"evidence": ev, "devices": [], "events": events, "analysis": None,
                               "custody": [{"timestamp": now, "action": "EVIDENCE_ACQUIRED", "actor": "tester",
                                            "description": "added <b>&"}]}],
           "report_id": "REPORT-ROCKET-000001", "generated_at": "2026-01-05 22:00:00 UTC", "generated_by": "tester"}
    out = tmp_path / "r.pdf"
    report_service.build_report_pdf(ctx, out)
    data = out.read_bytes()
    assert data.startswith(b"%PDF") and len(data) > 2000
    s = report_service.detection_summary(events)
    assert s["total_detections"] == 1 and s["motion_events"] == 1
    assert s["classes"]["person"]["mean_conf"] == pytest.approx(0.9)


# ---- pure modules added for auth / streaming / correlation / snapshots --------------------
def test_range_parsing():
    from app.utils.ranges import parse_range
    assert parse_range(None, 1000) is None
    assert parse_range("bytes=0-99", 1000) == (0, 99)
    assert parse_range("bytes=900-", 1000) == (900, 999)
    assert parse_range("bytes=-100", 1000) == (900, 999)
    assert parse_range("bytes=0-99999", 1000) == (0, 999)
    with pytest.raises(AppError) as e:
        parse_range("bytes=5000-", 1000)
    assert e.value.status_code == 416


def test_password_hash_and_jwt(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongomock://x")
    monkeypatch.setenv("JWT_SECRET", "s" * 40)
    from app import config
    config.get_settings.cache_clear()
    from app.services import auth_service as a
    h = a.hash_password("hunter2hunter2")
    assert "hunter2" not in h and a.verify_password("hunter2hunter2", h) and not a.verify_password("nope", h)
    tok = a.create_access_token({"user_id": "USR-1", "role": "investigator"})
    assert a.decode_access_token(tok)["sub"] == "USR-1"
    with pytest.raises(AppError):
        a.decode_access_token(tok + "x")


def test_correlation_is_temporal_only():
    from app.services.timeline_service import correlate
    t0 = datetime(2026, 1, 5, 10, 12, 4)
    mk = lambda i, cam, s, cls="person": {"event_id": str(i), "event_type": "object_detection", "class_name": cls,
                                          "camera_id": cam, "timestamp": t0 + timedelta(seconds=s),
                                          "evidence_id": "E", "video_time_seconds": s, "confidence": 0.9}
    g = correlate([mk(1, "CAM-01", 0), mk(2, "CAM-02", 5), mk(3, "CAM-01", 500), mk(4, "CAM-01", 0, "car")], 10)
    assert len(g) == 1 and g[0]["cameras"] == ["CAM-01", "CAM-02"] and g[0]["event_count"] == 2
    assert g[0]["label"] == "temporally correlated event" and "same_person" not in g[0]
    assert correlate([mk(1, "CAM-01", 0), mk(2, "CAM-01", 5)], 10) == []   # one camera: nothing


def test_snapshot_annotation_does_not_modify_source_frame(tmp_path):
    import numpy as np
    from app.ml.snapshots import save_annotated_frame
    frame = np.zeros((120, 160, 3), np.uint8)
    before = frame.copy()
    name = save_annotated_frame(frame, [{"class_name": "person", "confidence": 0.87,
                                         "bbox": {"x1": 10, "y1": 20, "x2": 80, "y2": 100}}], 1.5, tmp_path, 42)
    assert name == "frame_000042.jpg" and (tmp_path / name).stat().st_size > 0
    assert (frame == before).all()
