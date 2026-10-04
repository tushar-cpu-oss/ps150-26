"""Auth, streaming, snapshots, correlation, health, structured GET search (API level)."""
import pytest

from tests.test_api import StubDetector, _run


def test_register_login_me_and_role_not_client_settable(client):
    r = client.post("/api/auth/register", json={"full_name": "X", "email": "x@example.test", "password": "longenough1",
                                                "role": "admin"})
    assert r.status_code == 201 and r.json()["role"] == "investigator" and "password_hash" not in r.json()
    assert client.post("/api/auth/register", json={"full_name": "X", "email": "X@example.test",
                                                    "password": "longenough1"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "x@example.test", "password": "wrong"}).status_code == 401
    me = client.get("/api/auth/me").json()
    assert me["email"] == "rao@example.test" and me["role"] == "investigator"


def test_endpoints_require_jwt(client, case):
    for method, url in [("get", "/api/cases"), ("get", f"/api/cases/{case['case_id']}"),
                        ("get", "/api/evidence/EV-X"), ("get", "/api/timeline/CASE-X"),
                        ("get", "/api/chain-of-custody/EV-X"), ("post", "/api/reports/generate")]:
        r = getattr(client, method)(url, headers={"Authorization": ""})
        assert r.status_code == 401, url
    bad = client.get("/api/cases", headers={"Authorization": "Bearer not.a.jwt"})
    assert bad.status_code == 401 and bad.json()["error"]["code"] == "INVALID_TOKEN"
    assert client.get("/health", headers={"Authorization": ""}).status_code == 200


def test_expired_token_rejected(client, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "-1")
    get_settings.cache_clear()
    tok = client.post("/api/auth/login", json={"email": "rao@example.test", "password": "correct-horse-1"}).json()["access_token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "TOKEN_EXPIRED"


def test_case_investigator_comes_from_jwt_and_owner_isolation(client):
    r = client.post("/api/cases", json={"name": "Mine", "investigator": "Somebody Else"})
    c = r.json()
    assert c["investigator"] == "Insp. Rao" and c["investigator_id"] == client.user["user_id"]
    assert client.put(f"/api/cases/{c['case_id']}", json={"status": "in_progress"}).status_code == 422
    assert client.put(f"/api/cases/{c['case_id']}", json={"status": "closed"}).json()["status"] == "closed"
    client.post("/api/auth/register", json={"full_name": "Other", "email": "o@example.test", "password": "longenough1"})
    tok = client.post("/api/auth/login", json={"email": "o@example.test", "password": "longenough1"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get(f"/api/cases/{c['case_id']}", headers=h).status_code == 403
    assert client.get("/api/cases", headers=h).json() == []


def test_x_actor_header_is_ignored(client, evidence):
    client.post(f"/api/evidence/{evidence['evidence_id']}/verify", headers={"X-Actor": "Mallory"})
    rec = client.get(f"/api/chain-of-custody/{evidence['evidence_id']}").json()["records"]
    assert {r["actor"] for r in rec} == {"Insp. Rao"}


def test_stream_full_range_and_bad_range(client, evidence, video_path):
    eid = evidence["evidence_id"]
    data = video_path.read_bytes()
    full = client.get(f"/api/evidence/{eid}/stream")
    assert full.status_code == 200 and full.content == data and full.headers["accept-ranges"] == "bytes"
    part = client.get(f"/api/evidence/{eid}/stream", headers={"Range": "bytes=100-199"})
    assert part.status_code == 206 and part.content == data[100:200]
    assert part.headers["content-range"] == f"bytes 100-199/{len(data)}"
    tail = client.get(f"/api/evidence/{eid}/stream", headers={"Range": "bytes=-50"})
    assert tail.status_code == 206 and tail.content == data[-50:]
    assert client.get(f"/api/evidence/{eid}/stream", headers={"Range": f"bytes={len(data) + 10}-"}).status_code == 416
    # <video src> style: token in query string works ONLY on the stream endpoint
    anon = client.get(f"/api/evidence/{eid}/stream", params={"token": client.token}, headers={"Authorization": ""})
    assert anon.status_code == 200
    assert client.get(f"/api/evidence/{eid}", params={"token": client.token}, headers={"Authorization": ""}).status_code == 401


def test_snapshots_saved_and_served(client, evidence, monkeypatch):
    from app.ml import detector
    monkeypatch.setattr(detector, "get_detector", lambda *a, **k: StubDetector())
    job = _run(client, evidence, frame_sample_rate=1, motion_detection=False)
    assert job["status"] == "completed" and job["model"] == "stub.pt"
    snaps = client.get(f"/api/analysis/{job['analysis_id']}/snapshots").json()
    assert len(snaps) == 10 and snaps[1]["frame_number"] == 10 and snaps[1]["timestamp"] == pytest.approx(1.0)
    assert snaps[0]["detections"][0]["bbox"] == [1.0, 2.0, 30.0, 40.0]
    img = client.get(snaps[0]["image_url"])
    assert img.status_code == 200 and img.content[:3] == b"\xff\xd8\xff"
    assert client.get(f"/api/analysis/{job['analysis_id']}/snapshots/..%2F..%2Fx.jpg").status_code in (400, 404)
    assert client.get(f"/api/analysis/{job['analysis_id']}/snapshots/evil.txt").status_code == 400


def test_presets_and_health_and_get_search(client, case, evidence, monkeypatch):
    from app.ml import detector
    monkeypatch.setattr(detector, "get_detector", lambda *a, **k: StubDetector())
    job = _run(client, evidence, preset="fast", motion_detection=False)
    assert job["options"]["frame_sample_rate"] == 1.0 and job["counts"]["frames_analysed"] == 10
    h = client.get("/health").json()
    for k in ("status", "database", "ffprobe", "opencv", "ml_model"):
        assert k in h
    assert h["database"] == "connected" and h["ml"]["DEVICE"] == "cpu"
    r = client.get("/api/search", params={"case_id": case["case_id"], "object": "person", "camera": "CH-01",
                                          "from": "22:00:00", "to": "22:00:03"})
    assert r.status_code == 200 and r.json()["count"] == 4


def test_timeline_system_events_and_correlation(client, case, evidence, monkeypatch):
    from app.ml import detector
    monkeypatch.setattr(detector, "get_detector", lambda *a, **k: StubDetector())
    _run(client, evidence, frame_sample_rate=1, motion_detection=False)
    types = {e["event_type"] for e in client.get(f"/api/timeline/{case['case_id']}").json()["events"]}
    assert {"VIDEO_START", "VIDEO_END", "ANALYSIS_STARTED", "ANALYSIS_COMPLETED", "object_detection"} <= types
    # single camera -> nothing to correlate
    c = client.get(f"/api/timeline/{case['case_id']}/correlation").json()
    assert c["count"] == 0 and "does NOT establish" in c["disclaimer"]


def test_duplicate_analysis_409_names_running_job(client, evidence):
    """A queued/processing job must not be duplicated; the 409 tells the client which job to attach to."""
    from app.database import get_db
    from app.services import analysis_service
    job = analysis_service.create_job(get_db(), evidence["evidence_id"], {"motion_detection": True}, "tester")
    r = client.post("/api/analysis/video", json={"evidence_id": evidence["evidence_id"],
                                                  "options": {"motion_detection": True}})
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "ANALYSIS_IN_PROGRESS"
    assert err["details"]["analysis_id"] == job["analysis_id"]


def test_completed_job_reports_real_stages(client, evidence):
    """Stages are recorded by the pipeline, not estimated: decoding is skipped for a plain AVI."""
    from tests.test_api import _run
    job = _run(client, evidence, object_detection=False, motion_detection=True, face_detection=False)
    assert job["status"] == "completed" and job["stage"] is None
    by_name = {s["name"]: s["status"] for s in job["stages"]}
    assert by_name == {"integrity_check": "completed", "decoding": "skipped", "loading_models": "completed",
                       "frame_analysis": "completed", "building_timeline": "completed", "finalizing": "completed"}
