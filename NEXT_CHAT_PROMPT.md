# PROMPT FOR NEXT CHAT (paste everything below, then upload the latest zip)

You are continuing ROCKET FORENSICS (TEAM ROCKET): FastAPI + MongoDB + OpenCV/FFmpeg/YOLO backend, React/Vite/Tailwind/Three.js frontend.
Read `CHANGES-FINAL-PASS.md`, `docs/PS_COVERAGE_MATRIX.md`, `docs/PS150_AUDIT.md` first. Backend is source of truth; do not break
the validated baseline (46 pytest pass/1 skip, e2e 19/19). Never fake evidence, vendors, detections, progress %, or recovery.
First: in an environment WITH network, run `pip install -r backend/requirements.txt`, `pytest -q`, `python scripts/e2e_test.py`,
`cd frontend && npm install && npm run build` and fix any failures from the previous pass (it was never executed; the last two chats had no network, so pytest/e2e/npm build are still UNVERIFIED — only Python syntax compile was checked).

## ALREADY DONE (code-reviewed, unexecuted)
- Running analysis now polled via local active-job id; 409 returns running analysis_id and UI attaches to it
- Register → auto-login → /cases
- OEM adapter labels honest; detection tab wording; 409 test; PS coverage matrix

## LEFT TO DO — backend (in priority order)
1. Verify all of the above by running tests/build; fix regressions.
2. Per-stage analysis status (extracting_frames / object_detection / face / motion / building_timeline) stored on the job, so UI can show real stages. No fake %.
3. Timestamp normalization record per event: original, normalized, timezone, source (container/filename/sidecar/UPLOAD TIME), confidence, method. Mark upload-time fallback LOW confidence.
4. Upload-stage reporting (acquire → preserve → hash → metadata → format → verify) as real stage flags on the evidence doc.
5. Idempotent evidence upload (dedupe by case + SHA-256, return existing) and report generation.
6. Structured logging for auth/acquire/hash/analysis/report/custody (never log passwords/JWTs).
7. Validation hardening: malformed media, corrupt images, unsupported formats → `UNSUPPORTED / REQUIRES VENDOR DECODER`.
8. Optional real tracking (Ultralytics ByteTrack/BoT-SORT) with video-local IDs + "Track IDs are not identities" note.
9. Correlation: configurable window + event-type filter + explanatory "no match" reasons; verify camera labels.
10. Motion: configurable sensitivity/min-area exposed in API; duplicate-event suppression.
11. Report: add OBSERVED FACT / MODEL DETECTION / DERIVED RESULT / USER INTERPRETATION labels, analysis config, model version.
12. Security audit: path traversal, ownership checks on every case/evidence/report route, CORS, token-in-query for media only.

## LEFT TO DO — frontend
1. Landing: polish 3D EvidenceNetwork (particles, data packets, scan lines) without removing it; keep performant.
2. Upload UI with real stages (stage-based, no fake percentages) + completion summary.
3. Workstation: stage display from #2, disable START while running, filters ALL/PERSON/VEHICLE/FACE/MOTION/BOOKMARKS, snapshot cards with derived-artifact label and click-to-seek.
4. Evidence Vault chips (ACQUIRED/VERIFIED/ANALYZED/FAILED/PROCESSING/UNKNOWN) and "NO EVIDENCE ACQUIRED" empty state.
5. Integrity panel (SHA-256/MD5/SIZE/ORIGINAL PRESERVED), monospace wrapping hashes.
6. Correlation page flow (Camera A → event → window → Camera B) and "NO TEMPORAL MATCH FOUND" explanation.
7. Investigation archive empty state; real Settings (theme, animation intensity, confidence, motion sensitivity, timezone) only for settings that actually work; useful Help page.
8. Responsive pass (tablet), polling hygiene (stop on complete/fail/unmount), memoization for long lists.
9. Wording audit: "PERSON DETECTIONS" never "PEOPLE"; no unsourced numbers.

## LEFT TO DO — docs
Update README, ARCHITECTURE, SOP, USER_MANUAL, VALIDATION_REPORT (with REAL test output), OEM comparison, FINAL_TECHNICAL_REPORT; finalize PS matrix with test names.

## GENUINELY NOT POSSIBLE WITHOUT OEM DATA (keep labelled, never fake)
Proprietary filesystem parsing and direct acquisition for Dahua, Hikvision, CP Plus, Honeywell, TP-Link, Godrej, Uniview, Matrix;
OEM deleted-record reconstruction; facial identity recognition; cross-camera "same person" re-identification.

## FINAL DELIVERABLE
Updated zip, pytest + e2e + npm build output, PS matrix, remaining gaps, honest level (A/B/C/D — don't inflate; currently Level B).
