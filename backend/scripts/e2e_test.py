#!/usr/bin/env python3
"""REAL end-to-end test against a RUNNING server over HTTP (no mocks).

    uvicorn app.main:app --port 8000            # terminal 1 (MongoDB running, weights downloaded)
    python scripts/e2e_test.py path/to/cctv.mp4 # terminal 2  (omit path -> a synthetic clip is generated;
                                                #  YOLO will then legitimately find nothing)
Env: API=http://localhost:8000
Exit code 0 only if every step passed. Snapshots/detections are reported as counts, never assumed.
"""
import hashlib
import os
import sys
import time
import uuid
from pathlib import Path

import httpx

API = os.environ.get("API", "http://localhost:8000")
results = []


def step(name, ok, info=""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {info}")
    if not ok:
        raise SystemExit(f"Step failed: {name}")


def synth(path: Path) -> Path:
    import cv2
    import numpy as np
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (640, 360))
    for i in range(150):
        f = np.zeros((360, 640, 3), np.uint8)
        if 40 <= i < 100:
            x = (i * 8) % 500
            cv2.rectangle(f, (x, 120), (x + 90, 300), (255, 255, 255), -1)
        w.write(f)
    w.release()
    return path


def main():
    video = Path(sys.argv[1]) if len(sys.argv) > 1 else synth(Path("/tmp/e2e_clip.mp4"))
    raw = video.read_bytes()
    c = httpx.Client(base_url=API, timeout=600)
    h = c.get("/health").json()
    step("health", h["database"] == "connected" and h["ffprobe"] and h["opencv"], f"ml_model={h['ml_model']}")
    email = f"e2e_{uuid.uuid4().hex[:8]}@example.test"
    step("register", c.post("/api/auth/register", json={"full_name": "E2E Tester", "email": email,
                                                        "organization": "Team Rocket", "password": "e2e-password-1"}).status_code == 201)
    tok = c.post("/api/auth/login", json={"email": email, "password": "e2e-password-1"}).json()["access_token"]
    c.headers["Authorization"] = f"Bearer {tok}"
    step("me", c.get("/api/auth/me").json()["email"] == email)
    case = c.post("/api/cases", json={"name": "E2E case", "description": "end-to-end"}).json()
    step("create case", case["case_id"].startswith("CASE-"), case["case_id"])
    with open(video, "rb") as f:
        r = c.post("/api/evidence/upload", data={"case_id": case["case_id"], "camera_id": "CAM-01"},
                   files={"file": (video.name, f, "video/mp4")})
    step("upload", r.status_code == 201, r.text[:120] if r.status_code != 201 else "")
    ev = r.json()
    step("sha256 == local", ev["sha256"] == hashlib.sha256(raw).hexdigest())
    step("md5 == local", ev["md5"] == hashlib.md5(raw).hexdigest())
    m = ev["metadata"] or {}
    step("ffprobe metadata", bool(m.get("width") and m.get("fps") and m.get("duration")),
         f"{m.get('width')}x{m.get('height')} {m.get('fps')}fps {m.get('duration')}s {m.get('codec')}")
    v = c.post(f"/api/evidence/{ev['evidence_id']}/verify").json()
    step("verify integrity", v["integrity_status"] == "MATCH")
    r = c.get(f"/api/evidence/{ev['evidence_id']}/stream", headers={"Range": "bytes=0-1023"})
    step("stream 206", r.status_code == 206 and r.content == raw[:1024])
    dev = c.post("/api/devices/detect", json={"case_id": case["case_id"], "evidence_id": ev["evidence_id"]}).json()
    step("device identification", "identification_method" in dev, f"{dev['manufacturer']} ({dev['identification_method']})")
    a = c.post("/api/analysis/video", json={"evidence_id": ev["evidence_id"], "options": {"preset": "balanced"}})
    step("analysis queued", a.status_code == 202)
    aid = a.json()["analysis_id"]
    while True:
        j = c.get(f"/api/analysis/{aid}").json()
        print(f"      status={j['status']} progress={j['progress']:.2f}")
        if j["status"] in ("completed", "failed"):
            break
        time.sleep(2)
    step("analysis completed", j["status"] == "completed", str(j["counts"]))
    print("      modules:", j["modules"], "warnings:", j["warnings"], "model:", j.get("model"))
    snaps = c.get(f"/api/analysis/{aid}/snapshots").json()
    if snaps:
        img = c.get(snaps[0]["image_url"])
        step("snapshot image", img.status_code == 200 and img.content[:3] == b"\xff\xd8\xff", f"{len(snaps)} snapshots")
    else:
        print("[INFO] no snapshots (YOLO found no objects or model unavailable) - not faked")
    tl = c.get(f"/api/timeline/{case['case_id']}").json()
    step("timeline", tl["count"] > 0, f"{tl['count']} events; types={sorted({e['event_type'] for e in tl['events']})}")
    s = c.get("/api/search", params={"case_id": case["case_id"], "object": "motion"}).json()
    step("structured search (motion)", s["query_mode"] == "structured", f"{s['count']} results")
    corr = c.get(f"/api/timeline/{case['case_id']}/correlation").json()
    step("correlation endpoint", "disclaimer" in corr, f"{corr['count']} groups")
    coc = c.get(f"/api/chain-of-custody/{ev['evidence_id']}").json()
    step("chain of custody", {"EVIDENCE_ACQUIRED", "EVIDENCE_VERIFIED", "ANALYSIS_COMPLETED"} <= {x["action"] for x in coc["records"]}
         and all(x["actor_name"] == "E2E Tester" for x in coc["records"]))
    rep = c.post("/api/reports/generate", json={"case_id": case["case_id"]})
    step("report generated", rep.status_code == 201)
    pdf = c.get(rep.json()["download_url"])
    step("report is a PDF", pdf.content.startswith(b"%PDF"), f"{len(pdf.content)} bytes")
    Path("/tmp/e2e_report.pdf").write_bytes(pdf.content)
    print(f"\nALL {len(results)} STEPS PASSED. Report saved to /tmp/e2e_report.pdf")


if __name__ == "__main__":
    main()
