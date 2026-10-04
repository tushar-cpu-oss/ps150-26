# Final-pass changes (this session)

Verified only by Python compile + code reading. NOT executed: pytest, e2e, npm build (no network/deps).

1. **Bug fix – running analysis was never polled.** `evidence.latest_analysis_id` is set only on job completion, so
   the workstation could not follow a queued/processing job. `EvidenceWorkstation.tsx` now tracks the active job id locally.
2. **409 handling.** Backend `ANALYSIS_IN_PROGRESS` now returns `error.details = {analysis_id, status}`;
   `api/analysis.ts startAnalysis` attaches to that job instead of showing an error. (Same response code → contract unchanged.)
3. **Registration → auto-login → /cases.** Falls back to the login page with a clear toast if auto sign-in fails.
4. **Honest adapter status.** OEM adapters now read `ADAPTER ARCHITECTURE READY - REQUIRES OEM SAMPLE/PROTOCOL`
   (was `IDENTIFICATION ONLY`). Capability logic keyed on `"SUPPORTED"` is unchanged.
5. Detection tab label `PERSONS` → `PERSON DET.` (detections ≠ unique people).
6. New test `test_duplicate_analysis_409_names_running_job`.
7. New `docs/PS_COVERAGE_MATRIX.md`.

## Pass 4 (no network again — still NOT executed)
8. **Per-stage analysis status (backend + UI).** Job now stores `stage` and ordered `stages`
   (integrity_check, decoding, loading_models, frame_analysis, building_timeline, finalizing) with
   pending/running/completed/skipped/failed. Failures mark the running stage `failed`.
   New test `test_completed_job_reports_real_stages`. Stage transition logic was exercised against a fake
   collection (standalone); pytest itself was not run. Workstation shows the stage list.


## Final closure pass

This package additionally implements only capabilities that can be demonstrated without inventing OEM behavior:

- optional real Ultralytics ByteTrack tracking with video-local track IDs;
- explicit track IDs in detection/timeline artifacts and UI wording that they are not identities;
- uniform timestamp source/confidence/method provenance on generated detection and motion events;
- functional authenticated Settings and Help pages;
- reduced-motion workstation preference;
- updated PS coverage matrix.

The remaining OEM-specific gaps are intentionally honest: direct DVR/NVR acquisition, proprietary filesystem/index reconstruction, and vendor-specific deleted-record recovery still require validated OEM evidence/protocols.
