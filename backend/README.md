# ROCKET FORENSICS — Backend
**TEAM ROCKET · Multi-Vendor DVR/NVR Forensic Analysis Platform (hackathon PROTOTYPE)**

A FastAPI + MongoDB backend that turns exported CCTV/DVR evidence into a verifiable forensic workflow:

`create case → upload evidence → real hashes → real metadata → verify integrity → video analysis (motion + YOLO) → timeline → chain of custody → PDF report`

Every hash, metadata field, detection and confidence value comes from the actual file or the actual model output. Nothing is fabricated.

---
## ⚠ Known prototype limitations (read first)
- **Proprietary DVR/NVR filesystem parsing is NOT implemented.** Evidence enters as exported files (mp4/avi/mov/mkv/wav/jpg/png), not as a disk image or device connection.
- **Standard signature carving and optional Sleuth Kit deleted-file enumeration are implemented; a conservative OEM baseline inspector now fingerprints common markers and enumerates candidate recorder artifacts, while proprietary deleted-record reconstruction is not claimed.**
- **Vendor-specific acquisition protocols are NOT implemented.**
- Device/vendor identification is a **low-confidence keyword match** on real metadata tags/filename, otherwise `Unknown`. Investigators can enter device details manually (`source: investigator_entered`).
- AI detection is **general-purpose** YOLO object detection (all COCO classes by default; restrict with `YOLO_CLASSES`) plus OpenCV motion detection. No facial/identity recognition. Results require human validation.
- Absolute event times = `recording_start + video offset`. `recording_start` comes from (1) investigator-supplied `recording_start` on upload, else (2) container `creation_time`, else (3) upload time (`upload_time_fallback`). The source is stored per evidence and on each event (`metadata.timestamp_source`). Treat fallback times as unreliable.
- The prototype does **not** establish legal admissibility. Reports are labelled *PROTOTYPE FORENSIC ANALYSIS REPORT*.
- Authentication is JWT-based. The chain-of-custody actor always comes from the verified token (`X-Actor` is ignored). Case access is owner-checked on `/api/cases*`; other endpoints require login but do not yet check per-evidence ownership.
- Cross-camera correlation is **temporal only** (same class, different cameras, within a time window). It never claims the same person/vehicle.
- YOLO weights are not in the repo: run `python scripts/download_model.py`.

`GET /health` returns the same split as machine-readable data: `implemented` / `prototype_or_simulated` / `future`.

| Implemented | Prototype / simulated | Future |
|---|---|---|
| Case CRUD; upload validation; SHA-256 + MD5; re-verification; FFprobe metadata; OpenCV motion; YOLO detection; timeline; structured search; chain of custody; PDF report | "Acquisition" = file upload; vendor inference from tags | DVR filesystem parsing; deleted-file recovery; vendor protocols; natural-language search; auth/RBAC |

---
## Architecture
```
backend/app
├── main.py            app factory, CORS, error handlers
├── config.py          .env settings (pydantic-settings)
├── database.py        PyMongo client, indexes, atomic ID counters
├── routers/           thin HTTP layer → call services only
├── services/          all business logic
├── schemas/           Pydantic v2 request/response models
├── ml/                video.py (frame sampling) · motion.py · detector.py (YOLO)
└── utils/             safe file handling, errors, time helpers
storage/{evidence,processed,reports}
```
**Design notes**
- Sync PyMongo; endpoints are plain `def` (run in FastAPI's threadpool). Service functions take a `db` handle, so a Motor port is mechanical.
- Analysis runs via FastAPI `BackgroundTasks` (`POST /api/analysis/video` returns 202 immediately; poll `GET /api/analysis/{id}`). Jobs are in-process: a server restart mid-job leaves it `processing`. Use a real queue (Celery/RQ/Arq) for production.
- Original evidence is stored read-only (`chmod 440`), opened read-only, and its SHA-256 is re-checked before each analysis (job fails if it no longer matches).
- Timeline/search default to the **latest completed analysis per evidence**, so re-running analysis does not double-count. Pass `analysis_id` to see a specific run.
- Device `confidence` is categorical (`none` / `low` / `investigator_supplied`), never a made-up number. Motion events have `confidence: null` and a `motion_score` (fraction of frame area in moving regions).
- Motion events are debounced: continuous motion = one event; a pause ≥ `MOTION_GAP_SECONDS` starts a new one. `frame_number` is the event start.

## Tech stack
Python 3.12+, FastAPI, Pydantic v2, MongoDB (PyMongo), OpenCV, FFmpeg/FFprobe, Ultralytics YOLO, NumPy, ReportLab, pytest.

## Installation
```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # then edit
```
### FFmpeg setup
`ffprobe` must be on PATH (Ubuntu: `sudo apt install ffmpeg`; macOS: `brew install ffmpeg`; Windows: `winget install ffmpeg`). `/health` reports `dependencies.ffprobe`.

### MongoDB setup
- Docker (easiest): `docker compose up -d mongo`, then `MONGODB_URI=mongodb://localhost:27017` in `.env` if running the API outside Docker (the compose `mongo` service is not published to the host by default; add `ports: ["27017:27017"]` to reach it from the host, or run the API in compose too).
- Or install MongoDB locally / use Atlas and set `MONGODB_URI`.
- Indexes are created automatically on startup.

### YOLO model setup
Object detection needs Ultralytics weights. Options:
1. Put weights at `models/yolov8n.pt` and set `YOLO_MODEL_PATH=models/yolov8n.pt` (offline-safe).
2. Set `YOLO_MODEL_PATH=yolov8n.pt` and let Ultralytics download it on first use (needs internet).

If YOLO or the weights are unavailable, an analysis still runs motion detection and records `modules.object_detection = "unavailable"` with a warning — it never invents detections. If *only* object detection was requested, the job fails with the reason.

## Running
```bash
uvicorn app.main:app --reload            # http://<host>:8000/docs
# or everything in Docker:
mkdir -p models && cp /path/to/yolov8n.pt models/
docker compose up --build
```
## Tests
```bash
pytest -v
```
Uses `mongomock` (no MongoDB needed) and real generated video files. Covers: health, case CRUD, upload → evidence record, SHA-256/MD5 vs independent computation, tamper → verification fails, real metadata, upload rejections (extension/MIME/magic bytes/size/path traversal), motion grouping, detection records (timestamps/frames/confidence), chronological timeline, filters, structured search, chain of custody, PDF generation, CORS.
Note: the detection-pipeline tests use a clearly-labelled **stub detector** (no weights needed in CI); `test_real_yolo` exercises the real model when `ultralytics` + weights are present.

## Environment variables
| Variable | Meaning | Default |
|---|---|---|
| `MONGODB_URI` | **required** connection string | — |
| `MONGODB_DATABASE` | database name | `rocket_forensics` |
| `MAX_UPLOAD_SIZE_MB` | upload size limit | `500` |
| `YOLO_MODEL_PATH` | YOLO weights | `yolov8n.pt` |
| `YOLO_CONFIDENCE_THRESHOLD` | min detection confidence | `0.5` |
| `FRAME_SAMPLE_RATE` | analysed frames per second | `2` |
| `MOTION_THRESHOLD` | per-pixel diff (0–255) | `25` |
| `MIN_CONTOUR_AREA` | min moving area (px) | `500` |
| `MOTION_GAP_SECONDS` | motion debounce gap | `2.0` |
| `CORS_ORIGINS` | comma-separated origins | *(none)* |
| `APP_ENV` | `production` hides error details | `development` |
| `STORAGE_DIR` | storage root | `./storage` |

## API
Interactive docs at `/docs`. Errors are always `{"success": false, "error": {"code", "message"}}`.

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | status, dependency check, capability split |
| POST/GET | `/api/cases` | IDs `CASE-ROCKET-0001…` |
| GET/PATCH/DELETE | `/api/cases/{case_id}` | DELETE refused (409) if case has evidence — archive instead |
| POST | `/api/evidence/upload` | multipart: `case_id`, `file`, optional `camera_id`, `recording_start` (ISO-8601). IDs `EV-ROCKET-000001` |
| GET | `/api/evidence/{id}` | info, hashes, metadata, processing/analysis status |
| POST | `/api/evidence/{id}/verify` | re-hash and compare → `verified`, stored/current SHA-256 & MD5 |
| POST | `/api/devices` | manual investigator-entered device |
| POST | `/api/devices/detect` | `{case_id, evidence_id}` metadata inference; `Unknown` if nothing found |
| GET | `/api/devices/{case_id}` | |
| POST | `/api/analysis/video` | `{evidence_id, options:{object_detection, motion_detection, frame_sample_rate, confidence_threshold}}` → 202 `{analysis_id, status}` |
| GET | `/api/analysis/{analysis_id}` | status, progress, module status, warnings, counts |
| POST | `/api/analysis/search` | structured: `case_id, object_type ("person"/"car"/…/"motion"), start_time, end_time, minimum_confidence` |
| GET | `/api/timeline/{case_id}` | `start_time, end_time, event_type, camera_id, min_confidence` (+ `evidence_id, analysis_id, limit`), sorted chronologically |
| GET | `/api/chain-of-custody/{evidence_id}` | chronological audit records |
| POST | `/api/reports/generate` | `{case_id, evidence_ids?}` → `{report_id, download_url, …}` |
| GET | `/api/reports/{report_id}` · `/download` | metadata · the PDF |

`start_time`/`end_time` accept an ISO datetime (`2026-01-05T22:00:00Z`) **or** a UTC time of day (`22:00:00`, may cross midnight).

Send `X-Actor: <name>` to attribute custody records.

## Frontend integration
- Set `VITE_API_BASE_URL` in the frontend to this API's origin; add the frontend origin to `CORS_ORIGINS`.
- **Video seek:** each timeline event has `video_time_seconds` (use `video.currentTime = event.video_time_seconds`) and `frame_number` (≈ `frame_number / fps`, fps in evidence `metadata.fps`).
- **Timeline polling:** after `POST /api/analysis/video`, poll `GET /api/analysis/{id}` until `completed`/`failed`, then load the timeline.
- Evidence video playback is not served by this backend yet (add a range-request streaming endpoint if the UI must play server-side files, or play the local file the user selected).

## Future extensions
DVR/NVR image parsing and vendor modules · deleted-file carving · job queue + worker · authentication/RBAC and signed custody entries · evidence streaming endpoint · natural-language search layer over the structured search API · vendor-specific acquisition connectors · digital signatures on reports.


---
## Quick start (fresh machine)
```bash
sudo apt install ffmpeg mongodb   # or run MongoDB via docker: docker run -d -p 27017:27017 mongo:7
cd backend && python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # set JWT_SECRET (python -c "import secrets;print(secrets.token_urlsafe(48))")
python scripts/download_model.py  # YOLO weights -> models/yolo11n.pt
uvicorn app.main:app --reload     # docs: http://localhost:8000/docs   health: /health
# or: docker compose up --build   (put weights in ./models first)
```
Tests: `pytest -q` (uses mongomock; `tests/test_api.py::test_real_yolo` runs only if weights exist).
Real HTTP end-to-end: `python scripts/e2e_test.py /path/to/cctv.mp4` against the running server.

## API (all `/api/*` need `Authorization: Bearer <jwt>`; media URLs also accept `?token=`)
Success responses return the resource directly; errors are `{"success": false, "error": {"code","message","details?"}}`.

| Method | Path | Purpose |
|---|---|---|
| POST | /api/auth/register, /api/auth/login | create investigator account / get JWT (public) |
| GET | /api/auth/me | current user |
| GET/POST | /api/cases | list (own cases; admin sees all) / create (investigator = JWT user) |
| GET/PUT | /api/cases/{case_id} | read / update name, description, status |
| POST | /api/evidence/upload | multipart: case_id, file, camera_id?, recording_start? |
| GET | /api/evidence/{id} | evidence + hashes + metadata |
| GET | /api/evidence/{id}/stream | original file, HTTP Range (206) |
| POST | /api/evidence/{id}/verify | recompute MD5/SHA-256 -> `integrity_status` MATCH/TAMPERED |
| POST | /api/devices/detect, /api/devices | metadata-based vendor inference (else Unknown / insufficient_evidence) / manual entry |
| POST | /api/analysis/video | options: object_detection, motion_detection, preset fast/balanced/deep, frame_sample_rate, confidence_threshold -> 202 + analysis_id |
| GET | /api/analysis/{id} | status, progress, model, model_version, options, counts, warnings |
| GET | /api/analysis/{id}/snapshots (+ /{file}) | annotated detection frames |
| GET | /api/timeline/{case_id} | chronological events; `video_time_seconds` = seek offset |
| GET | /api/timeline/{case_id}/correlation | temporal cross-camera groups |
| GET | /api/search?case_id&object&camera&from&to | structured search (POST /api/analysis/search also works) |
| GET | /api/chain-of-custody/{evidence_id} | append-only custody log |
| POST | /api/reports/generate; GET /api/reports/{id}[/download] | PDF report |
| GET | /health | db, ffprobe, opencv, ml model status |

Make an admin: `db.users.updateOne({email:"you@x.com"},{$set:{role:"admin"}})` (roles are never client-settable).

## Status
IMPLEMENTED: everything above, plus standard network stream acquisition through FFmpeg and forensic-image OEM baseline inspection. NOT IMPLEMENTED: proprietary DVR/NVR filesystem/format parsing (adapters in
`services/vendor_adapters.py` now includes real FFmpeg CCTV-container adapters plus explicit OEM identification-only boundaries; deleted-file recovery supports standard signature carving and optional Sleuth Kit enumeration, while OEM DVR record reconstruction remains unsupported; face detection is implemented, but face/person re-identification and natural-language search remain unsupported.
Case statuses are `active | archived | closed` (not OPEN/IN_PROGRESS/CLOSED).
