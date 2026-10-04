# Rocket Forensics — Integrated Frontend + Backend

This package connects the existing Rocket Forensics UI to the FastAPI backend without redesigning the UI.

## Local setup

### Backend
1. Start MongoDB.
2. In `backend/`, create `.env` from `.env.example`.
3. Set:
   - `MONGODB_URI=mongodb://localhost:27017`
   - `FRONTEND_ORIGIN=http://localhost:5173`
   - a strong local `JWT_SECRET`
4. Install `backend/requirements.txt`.
5. Make sure FFmpeg/ffprobe is on PATH.
6. If object detection is required, install the ML dependencies and place the configured YOLO weights under `backend/models/`.
7. Run the FastAPI app with the project's normal uvicorn command.

### Frontend
1. In `frontend/`, run `npm install`.
2. `frontend/.env` is configured for:
   `VITE_API_BASE_URL=http://localhost:8000`
3. Run `npm run dev`.

## Integration changes

- Authentication now finishes loading immediately when there is no token and clears invalid sessions.
- Case creation maps the existing UI title to backend `name`; backend-generated `case_id`/`case_number` are used afterward.
- Evidence upload uses `POST /api/evidence/upload` multipart form data.
- Evidence IDs are normalized from backend `evidence_id`.
- Video and snapshot media use `?token=JWT`.
- Analysis uses `/api/analysis/video` then polls `/api/analysis/{analysis_id}`.
- Detection and motion data are read from the real case timeline.
- Timeline clicks preserve `video_time_seconds` and seek the evidence video.
- Search uses the structured `/api/search` endpoint.
- Correlation uses `/api/timeline/{case_id}/correlation` and retains the backend disclaimer.
- Chain of custody is loaded per evidence item and combined client-side for the case ledger.
- Reports use `/api/reports/generate`, `/api/reports/{report_id}`, and `/download`.
- Device identification uses `/api/devices/detect`; unknown results remain `UNKNOWN / INSUFFICIENT EVIDENCE`.
- No frontend `fetch()` calls are scattered outside the central API client.
- Mock/placeholder forensic records were not introduced.

## Small backend addition

The supplied backend had a case evidence listing service but no router endpoint for it. The integrated package adds:

`GET /api/evidence?case_id=<case_id>`

It returns the existing `EvidenceOut` records for that case and is authenticated by the existing evidence router. No existing API contract was rewritten.

## Verification status

The source was statically checked and Python application code compiles.

Full frontend build/lint and live end-to-end testing could not be completed in this execution environment because external package installation is unavailable:
- `npm install` could not reach the npm registry, so Vite/React dependencies are absent.
- `npm run build` / `npm run lint` stop at missing `vite/client`.
- `npm run dev` cannot start because `vite` is not installed.
- Backend integration tests cannot initialize because `pymongo` and `mongomock` are not installed, and package installation cannot reach PyPI.
- `ffmpeg`/`ffprobe` are present in the environment.
- OpenCV, NumPy and ReportLab are present.
- `ultralytics` and YOLO weights are not present, so real object-detection analysis would also be blocked here.

A real MP4, MongoDB instance and the backend's ML dependencies/weights are therefore still required for the requested 16-step live end-to-end test.


## PS-150 audit artifacts

See `docs/` for the acceptance audit, OEM comparison, architecture, SOP, validation report, user manual, limitations, and final technical report. `backend/app/services/forensic_image_service.py` is an explicit read-only forensic-image intake extension boundary; it does not parse or mount images.
