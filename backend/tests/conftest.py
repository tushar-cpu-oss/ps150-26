import os
from pathlib import Path

import pytest

from tests.helpers import make_video


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Fresh app + in-memory MongoDB (mongomock) + temp storage for every test."""
    monkeypatch.setenv("MONGODB_URI", "mongomock://tests")
    monkeypatch.setenv("MONGODB_DATABASE", "rocket_test")
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "5")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("CORS_ORIGINS", "http://example.test")
    from app import config, database
    config.get_settings.cache_clear()
    database.reset_client()
    from fastapi.testclient import TestClient
    from app.main import create_app
    monkeypatch.setenv("JWT_SECRET", "test-secret-test-secret-test-secret")
    config.get_settings.cache_clear()
    with TestClient(create_app()) as c:
        c.storage = tmp_path / "storage"
        reg = c.post("/api/auth/register", json={"full_name": "Insp. Rao", "email": "rao@example.test",
                                                  "organization": "Test Unit", "password": "correct-horse-1"})
        assert reg.status_code == 201, reg.text
        login = c.post("/api/auth/login", json={"email": "rao@example.test", "password": "correct-horse-1"})
        c.token = login.json()["access_token"]
        c.user = login.json()["user"]
        c.headers.update({"Authorization": f"Bearer {c.token}"})
        yield c
    config.get_settings.cache_clear()
    database.reset_client()


@pytest.fixture()
def video_path(tmp_path) -> Path:
    return make_video(tmp_path / "cctv_clip.avi")


@pytest.fixture()
def case(client):
    r = client.post("/api/cases", json={"name": "Test case", "description": "d"})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture()
def evidence(client, case, video_path):
    with open(video_path, "rb") as f:
        r = client.post("/api/evidence/upload",
                        data={"case_id": case["case_id"], "camera_id": "CH-01",
                              "recording_start": "2026-01-05T22:00:00Z"},
                        files={"file": ("cctv_clip.avi", f, "video/x-msvideo")})
    assert r.status_code == 201, r.text
    return r.json()
