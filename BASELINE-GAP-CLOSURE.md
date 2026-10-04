# ROCKET FORENSICS — Baseline Gap Closure

This pass adds only low-risk, technically demonstrable baseline capabilities around the remaining PS gaps.

## Added

- **Standard network stream acquisition**: authenticated `POST /api/acquisition/network` captures RTSP/RTSPS/HTTP/HTTPS/RTMP/RTMPS streams through local FFmpeg, stores the capture as immutable evidence, hashes it, extracts metadata, and creates custody events.
- **OEM baseline image inspection**: `GET /api/forensic-images/{image_id}/oem-baseline` scans a bounded image prefix for common OEM markers and, when Sleuth Kit is available, enumerates candidate media/recorder artifacts.
- **Candidate deleted artifacts**: baseline inspection includes standard deleted-file enumeration where `fls` is available.
- **Frontend**: Evidence Vault now exposes a Standard Network Acquisition form.

## Still intentionally not claimed

- OEM-private DVR/NVR acquisition protocols.
- Proprietary filesystem/index reconstruction.
- OEM-specific deleted database reconstruction.

These are not being represented as complete merely because a baseline scanner or standard stream capture exists.
