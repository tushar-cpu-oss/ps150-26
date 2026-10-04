# PS Coverage Matrix

Status vocabulary: IMPLEMENTED · PARTIAL · PROTOTYPE · ADAPTER READY · REQUIRES OEM SAMPLE/PROTOCOL · NOT IMPLEMENTED

Source of statuses: the code audit in `docs/PS150_AUDIT.md` plus the code review done in the final pass
(see `CHANGES-FINAL-PASS.md`). **Statuses were assigned by reading code; the full test suite and the
frontend build have NOT been executed since this pass (no PyPI/npm access in that environment).**
Re-run `pytest -q`, `python scripts/e2e_test.py`, `npm run build` before presenting.

| # | Requirement | Implementation / module | Endpoint | UI location | Test | Status |
|---|---|---|---|---|---|---|
| 1 | Multi-vendor architecture | `services/vendor_adapters.py` registry | `GET /api/devices/...` | Evidence → device panel | test_core_modules | IMPLEMENTED (registry) |
| 2 | Automatic device identification | `device_inference.py`, `device_service.py` (filename/metadata evidence) | `POST /api/devices/detect` | Evidence detail | test_api/test_features | PARTIAL – heuristic only; unknown stays `UNKNOWN / INSUFFICIENT EVIDENCE` |
| 3 | Forensic acquisition (files) | `evidence_service.py`, `utils/files.py` | `POST /api/evidence/upload` | Evidence vault uploader | test_api, e2e | IMPLEMENTED |
| 4 | Forensic image ingest (DD/IMG/RAW) | `forensic_image_service.py` | `/api/forensic-images/*` | Case → forensic image uploader | test_ps150_extensions (isolated) | PARTIAL – E01 and Sleuth Kit depend on installed tools |
| 5 | Proprietary filesystem parsing (Dahua, Hikvision, CP Plus, Honeywell, TP-Link, Godrej, Uniview, Matrix) | `OemIdentificationAdapter` (raises NotImplementedError) | – | Capability matrix | – | REQUIRES OEM SAMPLE/PROTOCOL (ADAPTER ARCHITECTURE READY) |
| 6 | Direct DVR/NVR device acquisition | – | – | – | – | NOT IMPLEMENTED |
| 7 | Video extraction | FFmpeg/OpenCV, `decoder_service.py` | `GET /api/evidence/{id}/stream` | Video player | test_api, e2e | IMPLEMENTED |
| 8 | Metadata extraction | `metadata_service.py` (FFprobe, OpenCV fallback) | `/api/evidence/{id}` | Evidence detail | test_api, e2e | IMPLEMENTED |
| 9 | Proprietary format decoding | FFmpeg demux for `.dav`/`.ifv`/raw H.264/H.265 | via analysis | Upload → analysis | isolated only | PARTIAL – only what FFmpeg can demux; no real OEM sample tested |
| 10 | Deleted footage recovery | `recovery_service.py` (signature carving, TSK `fls` if installed) | `/api/forensic-images/*` | Forensic image view | synthetic carve test | PARTIAL – standard carving only; no OEM DB/index reconstruction |
| 11 | Timestamp normalization | `utils/timeutil.py`, evidence `recording_start` + source/confidence/method provenance | timeline | Timeline | test_core_modules | PARTIAL – provenance is now stored uniformly for generated events; recorder clock synchronization remains unavailable without source metadata |
| 12 | MD5 + SHA-256 (chunked) | `hashing_service.py` | upload, `/verify` | Integrity panel | test_core_modules, e2e | IMPLEMENTED |
| 13 | Cross-camera correlation (temporal) | `timeline_service.py` | `GET /api/timeline/{case}/correlation` | Correlation page | test_features | IMPLEMENTED – temporal only, never "same person" |
| 14 | Chain of custody | `custody_service.py` (append-only, actor-stamped) | `/api/custody/*` | Custody ledger | test_api | IMPLEMENTED |
| 15 | Forensic PDF report | `report_service.py` (ReportLab) | `/api/reports/*` | Reports | test_api, e2e | IMPLEMENTED |
| 16 | Object detection (YOLO) | `ml/detector.py` | `/api/analysis/video` | Workstation | stub-tested; real model in e2e | IMPLEMENTED (needs weights in `backend/models/`) |
| 17 | Face detection | `ml/face.py` (Haar) – detection only | analysis | Workstation | isolated | IMPLEMENTED (detection); identity recognition NOT IMPLEMENTED by design |
| 18 | Motion detection | `ml/motion.py` | analysis | Timeline | test_api | IMPLEMENTED |
| 19 | Object tracking (ByteTrack/BoT-SORT) | `ml/detector.py` via Ultralytics ByteTrack | `/api/analysis/video` option `object_tracking` | Analysis workstation | model-dependent / optional | IMPLEMENTED (optional, video-local track IDs; no identity recognition) |
| 20 | Analysis job lifecycle (queued/processing/completed/failed) + duplicate guard | `analysis_service.py`; 409 now returns the running `analysis_id` | `/api/analysis/*` | Workstation | test_features | IMPLEMENTED (real pipeline stages plus progress) |
| 21 | Search | `timeline_service.search` | `POST /api/analysis/search` | Search page | test_api | IMPLEMENTED (structured filters) |
| 22 | OEM comparison, SOP, manual, validation, final report | `docs/*` | – | – | – | IMPLEMENTED (documentation) |
