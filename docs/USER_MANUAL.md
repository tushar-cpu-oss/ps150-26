# Rocket Forensics User Manual

## 1. Registration and login

Register an investigator account and log in. The API issues a bearer JWT used for protected operations.

## 2. Case creation

Create a case from the case workspace. The backend generates the case identifier.

## 3. Evidence acquisition

Open the evidence workspace and upload a supported standard video export. Optionally provide camera ID and recording start.

The platform computes MD5 and SHA-256 and extracts container metadata.

## 4. Verification

Use the evidence verification action to recompute both hashes. A matching result is shown as `MATCH`; a mismatch is recorded as `TAMPERED`.

## 5. Device identification

Run device detection after evidence upload. The current implementation uses metadata/filename keyword inference and reports low confidence. If evidence is insufficient, the vendor remains `Unknown`.

Manual device information can also be recorded.

## 6. Video analysis

Start video analysis with motion detection and/or object detection. Motion detection is available through OpenCV. Object detection requires a configured Ultralytics YOLO model file.

The analysis job exposes status, progress, module status, warnings and counts.

## 7. Timeline

Review chronological video/system events. Events can be filtered by time, camera, evidence, event type and confidence.

## 8. Search

Use structured search for object class, motion, camera, time range, confidence and evidence.

Natural-language search is not implemented.

## 9. Cross-camera correlation

The correlation view groups object-class events occurring on different cameras within a time window. It is explicitly temporal correlation and does not identify a person or vehicle.

## 10. Chain of custody

Open the chain-of-custody records for evidence. Records include actor, action, timestamp, evidence ID, hash and description.

## 11. Report generation

Generate a PDF report for a case/evidence set. The report includes evidence, hashes, metadata, device information, analysis, timeline, correlation context, custody records and limitations.

## 12. Unsupported features

Proprietary filesystem parsing, proprietary DVR format decoding, deleted-footage recovery, forensic-image parsing, face recognition and person re-identification are not presented as working features.
