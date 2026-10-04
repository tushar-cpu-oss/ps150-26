"""API-level tests (FastAPI TestClient + mongomock). Background tasks run inside the request."""
import hashlib
import os
import sys

import pytest


def _stored_file(client):
    return next((client.storage / "evidence").glob("EV-*"))


class StubDetector:
    """TEST DOUBLE that follows the YoloDetector interface. It lets the pipeline (timestamps,
    frame numbers, storage, timeline) be tested without model weights. Real-model behaviour is
    covered by test_real_yolo (skipped unless ultralytics + weights are available)."""
    model_name, model_version = "stub.pt", "stub-1"

    def detect(self, frame, confidence):
        return [{"class_name": "person", "class_id": 0, "confidence": 0.87, "bbox": {"x1": 1.0, "y1": 2.0, "x2": 30.0, "y2": 40.0}}]


# ---- system / cases -------------------------------------------------------------------
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["product"] == "ROCKET FORENSICS" and body["team"] == "TEAM ROCKET"
    assert body["dependencies"]["mongodb"] == "up"
    assert "Proprietary DVR/NVR filesystem parsing" in body["capabilities"]["future"]


def test_case_create_and_retrieve(client):
    r = client.post("/api/cases", json={"name": "A", "investigator": "I"})
    assert r.status_code == 201
    c = r.json()
    assert c["case_id"] == "CASE-ROCKET-0001" and c["status"] == "active"
    assert client.post("/api/cases", json={"name": "B", "investigator": "I"}).json()["case_id"] == "CASE-ROCKET-0002"
    assert client.get(f"/api/cases/{c['case_id']}").json()["name"] == "A"
    assert len(client.get("/api/cases").json()) == 2
    r = client.patch(f"/api/cases/{c['case_id']}", json={"status": "archived"})
    assert r.json()["status"] == "archived"
    assert client.delete(f"/api/cases/{c['case_id']}").status_code == 204
    r = client.get(f"/api/cases/{c['case_id']}")
    assert r.status_code == 404 and r.json() == {
        "success": False, "error": {"code": "CASE_NOT_FOUND", "message": "Case was not found."}}


def test_validation_error_format(client):
    r = client.post("/api/cases", json={"name": ""})
    assert r.status_code == 422 and r.json()["success"] is False
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


# ---- evidence / hashing ---------------------------------------------------------------
def test_upload_creates_evidence_with_correct_hashes(client, case, evidence, video_path):
    data = video_path.read_bytes()
    assert evidence["evidence_id"] == "EV-ROCKET-000001"
    assert evidence["sha256"] == hashlib.sha256(data).hexdigest()
    assert evidence["md5"] == hashlib.md5(data).hexdigest()
    assert evidence["file_size"] == len(data)
    got = client.get(f"/api/evidence/{evidence['evidence_id']}").json()
    assert got["processing_status"] == "metadata_extracted" and got["analysis_status"] == "not_started"
    assert "stored_filename" not in got and "storage_path" not in got  # server paths are not exposed
    assert client.get(f"/api/cases/{case['case_id']}").json()["evidence_count"] == 1


def test_video_metadata_is_real(evidence):
    m = evidence["metadata"]
    assert (m["width"], m["height"], m["frame_count"]) == (320, 240, 100)
    assert m["fps"] == pytest.approx(10.0) and m["duration"] == pytest.approx(10.0, abs=0.2)
    assert m["codec"] == "mjpeg" and m["video_streams"] == 1 and m["audio_streams"] == 0


def test_verify_passes_then_fails_after_modification(client, evidence):
    eid = evidence["evidence_id"]
    ok = client.post(f"/api/evidence/{eid}/verify").json()
    assert ok["verified"] is True and ok["stored_sha256"] == ok["current_sha256"]
    assert ok["integrity_status"] == "MATCH"
    path = _stored_file(client)
    os.chmod(path, 0o644)
    with open(path, "ab") as f:
        f.write(b"tampered")
    bad = client.post(f"/api/evidence/{eid}/verify").json()
    assert bad["verified"] is False and bad["integrity_status"] == "TAMPERED"
    assert bad["stored_sha256"] != bad["current_sha256"] and bad["stored_md5"] != bad["current_md5"]


def test_upload_rejections(client, case):
    cid = case["case_id"]

    def up(name, content, ctype="video/mp4"):
        return client.post("/api/evidence/upload", data={"case_id": cid}, files={"file": (name, content, ctype)})

    assert up("malware.exe", b"MZ\x00\x00").status_code == 415
    assert up("fake.mp4", b"MZ\x90\x00" + b"\0" * 64).json()["error"]["code"] == "CONTENT_MISMATCH"
    assert up("a.mp4", b"\0" * 32, "text/html").json()["error"]["code"] == "MIME_TYPE_MISMATCH"
    big = b"RIFF\0\0\0\0AVI " + b"\0" * (6 * 1024 * 1024)
    assert up("big.avi", big, "video/x-msvideo").status_code == 413
    assert list((client.storage / "evidence").glob("EV-*")) == []  # nothing left behind
    r = client.post("/api/evidence/upload", data={"case_id": "CASE-NOPE"},
                    files={"file": ("a.avi", b"RIFF\0\0\0\0AVI x", "video/x-msvideo")})
    assert r.status_code == 404


def test_path_traversal_filename_is_neutralised(client, case, video_path):
    with open(video_path, "rb") as f:
        r = client.post("/api/evidence/upload", data={"case_id": case["case_id"]},
                        files={"file": ("../../../etc/evil.avi", f, "video/x-msvideo")})
    assert r.status_code == 201 and r.json()["original_filename"] == "evil.avi"
    assert _stored_file(client).parent == client.storage / "evidence"


# ---- devices --------------------------------------------------------------------------
def test_device_detection_does_not_guess(client, case, evidence):
    r = client.post("/api/devices/detect", json={"case_id": case["case_id"], "evidence_id": evidence["evidence_id"]})
    d = r.json()
    assert r.status_code == 200 and d["manufacturer"] == "Unknown" and d["confidence"] is None
    assert d["identification_method"] == "insufficient_evidence"
    assert d["confidence_basis"] == "Vendor could not be determined from available evidence metadata."
    r = client.post("/api/devices", json={"case_id": case["case_id"], "manufacturer": "Dahua", "model": "XVR"})
    assert r.status_code == 201 and r.json()["source"] == "investigator_entered"
    assert len(client.get(f"/api/devices/{case['case_id']}").json()) == 2


# ---- analysis / timeline / search -----------------------------------------------------
def _run(client, evidence, **opts):
    r = client.post("/api/analysis/video", json={"evidence_id": evidence["evidence_id"], "options": opts})
    assert r.status_code == 202 and r.json()["analysis_id"].startswith("ANALYSIS-ROCKET-")
    return client.get(f"/api/analysis/{r.json()['analysis_id']}").json()


def test_motion_analysis_and_seek_fields(client, case, evidence):
    job = _run(client, evidence, object_detection=False, motion_detection=True)
    assert job["status"] == "completed" and job["counts"]["motion_events"] == 2
    ev = client.get(f"/api/timeline/{case['case_id']}", params={"event_type": "motion"}).json()["events"]
    assert [e["event_type"] for e in ev] == ["motion", "motion"]
    assert all(e["frame_number"] is not None and e["video_time_seconds"] is not None for e in ev)
    assert all(e["confidence"] is None for e in ev)  # motion has no invented confidence


def test_detection_records_and_timeline(client, case, evidence, monkeypatch):
    from app.ml import detector
    monkeypatch.setattr(detector, "get_detector", lambda *a, **k: StubDetector())
    job = _run(client, evidence, frame_sample_rate=1)
    assert job["status"] == "completed" and job["counts"]["detections"] == 10
    tl = client.get(f"/api/timeline/{case['case_id']}").json()
    stamps = [e["timestamp"] for e in tl["events"]]
    # 10 detections + 2 motion + VIDEO_START/END + ANALYSIS_STARTED/COMPLETED
    assert stamps == sorted(stamps) and tl["count"] == 16
    assert stamps[0].startswith("2026-01-05T22:00:00")               # recording_start + video offset
    det = [e for e in tl["events"] if e["event_type"] == "object_detection"]
    assert det[1]["frame_number"] == 10 and det[1]["video_time_seconds"] == pytest.approx(1.0)
    assert all(e["confidence"] == pytest.approx(0.87) and e["camera_id"] == "CH-01" for e in det)
    assert client.get(f"/api/evidence/{evidence['evidence_id']}").json()["analysis_status"] == "completed"


def test_timeline_filtering_and_search(client, case, evidence, monkeypatch):
    from app.ml import detector
    monkeypatch.setattr(detector, "get_detector", lambda *a, **k: StubDetector())
    _run(client, evidence, frame_sample_rate=1)
    cid = case["case_id"]
    g = lambda **q: client.get(f"/api/timeline/{cid}", params=q).json()
    assert g(event_type="motion")["count"] == 2
    assert g(min_confidence=0.9)["count"] == 0
    assert g(event_type="object_detection", start_time="22:00:05")["count"] == 5
    assert g(camera_id="CH-99")["count"] == 0
    assert g(start_time="2026-01-05T22:00:00Z", end_time="2026-01-05T22:00:02Z", event_type="object_detection")["count"] == 3
    assert client.get(f"/api/timeline/{cid}", params={"start_time": "junk"}).status_code == 422
    r = client.post("/api/analysis/search", json={
        "case_id": cid, "object_type": "person", "start_time": "22:00:00", "end_time": "22:00:03",
        "minimum_confidence": 0.70}).json()
    assert r["query_mode"] == "structured" and r["count"] == 4
    assert client.post("/api/analysis/search", json={"case_id": cid, "object_type": "car"}).json()["count"] == 0


def test_analysis_without_yolo_reports_honestly(client, case, evidence, monkeypatch):
    from app.ml import detector

    def boom(*a, **k):
        raise detector.DetectorUnavailable("weights missing")
    monkeypatch.setattr(detector, "get_detector", boom)
    job = _run(client, evidence)
    assert job["status"] == "completed" and job["modules"]["object_detection"] == "unavailable"
    assert job["counts"]["detections"] == 0 and "weights missing" in job["warnings"][0]
    job = _run(
    client,
    evidence,
    object_detection=True,
    motion_detection=False,
    face_detection=False,
)   # only YOLO requested, and it is unavailable
    assert job["status"] == "failed"


def test_analysis_aborts_if_evidence_tampered(client, evidence):
    path = _stored_file(client)
    os.chmod(path, 0o644)
    with open(path, "ab") as f:
        f.write(b"x")
    job = _run(client, evidence, object_detection=False)
    assert job["status"] == "failed" and "integrity" in job["error"].lower()


# ---- chain of custody / reports -------------------------------------------------------
def test_chain_of_custody_chronological(client, evidence):
    eid = evidence["evidence_id"]
    client.post(f"/api/evidence/{eid}/verify")
    _run(client, evidence, object_detection=False)
    rec = client.get(f"/api/chain-of-custody/{eid}").json()["records"]
    assert [r["action"] for r in rec] == ["EVIDENCE_ACQUIRED", "HASH_GENERATED", "EVIDENCE_VERIFIED",
                                          "ANALYSIS_STARTED", "ANALYSIS_COMPLETED"]
    assert [r["timestamp"] for r in rec] == sorted(r["timestamp"] for r in rec)
    assert all(r["sha256"] == evidence["sha256"] for r in rec) and rec[0]["actor"] == "Insp. Rao"
    assert all(r["actor_user_id"] == client.user["user_id"] and r["actor_name"] == "Insp. Rao" for r in rec)
    assert client.get("/api/chain-of-custody/EV-NOPE").status_code == 404


def test_report_generation(client, case, evidence):
    _run(client, evidence, object_detection=False)
    r = client.post("/api/reports/generate", json={"case_id": case["case_id"]})
    assert r.status_code == 201
    rep = r.json()
    assert rep["report_id"] == "REPORT-ROCKET-000001"
    pdf = client.get(rep["download_url"])
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert hashlib.sha256(pdf.content).hexdigest() == rep["sha256"]
    assert client.get(f"/api/reports/{rep['report_id']}").json()["filename"] == rep["filename"]
    actions = [x["action"] for x in client.get(f"/api/chain-of-custody/{evidence['evidence_id']}").json()["records"]]
    assert actions[-1] == "REPORT_GENERATED"
    assert client.post("/api/reports/generate", json={"case_id": "CASE-NOPE"}).status_code == 404


def test_cors_configured_from_env(client):
    r = client.options("/health", headers={"Origin": "http://example.test", "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") == "http://example.test"


def test_real_yolo(client, case, evidence):
    """Runs only when ultralytics AND local weights exist. Synthetic video has no people, so we
    only assert that whatever the real model returns is stored with real confidences in [0,1]."""
    pytest.importorskip("ultralytics")
    from app.config import get_settings
    if not get_settings().yolo_model_file.exists():
        pytest.skip("YOLO weights not present")
    job = _run(client, evidence)
    assert job["status"] == "completed" and job["modules"]["object_detection"] == "completed"
    for e in client.get(f"/api/timeline/{case['case_id']}", params={"event_type": "object_detection"}).json()["events"]:
        assert 0 <= e["confidence"] <= 1
