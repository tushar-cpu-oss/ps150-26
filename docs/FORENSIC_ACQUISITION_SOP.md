# Prototype Forensic Acquisition SOP

## 1. Create case
Create an authenticated case and record the case description.

## 2. Identify source
Record the camera/source identifier and any available recorder/device information. Do not infer an OEM when evidence is insufficient.

## 3. Acquire evidence
Upload a lawful standard exported video artifact. Record the original filename, file size, MIME type and acquisition actor.

Direct DVR/NVR acquisition and proprietary storage acquisition are not implemented.

## 4. Record acquisition information
Where available, provide the recording start as an ISO-8601 timestamp. The system records the source of the timestamp.

## 5. Hash evidence
The platform computes MD5 and SHA-256 over the stored file bytes.

## 6. Verify integrity
Run evidence verification. A mismatch is recorded as an integrity failure.

## 7. Preserve original
The stored evidence file is treated as read-only. Analysis checks its SHA-256 before processing.

## 8. Analyze a working/read-only copy
Run motion analysis and, when the configured YOLO weights are available, object detection. Annotated snapshots are stored separately from the evidence file.

## 9. Record events
Timeline events contain timestamps/video offsets and, for detections, class/confidence/frame information.

## 10. Maintain chain of custody
Acquisition, hash generation, verification, analysis and report-generation events are recorded with the authenticated actor context.

## 11. Generate report
Generate the prototype PDF report. Review the limitations section before using it for any formal purpose.

## Important boundary
This SOP does not substitute for an organizational forensic procedure, evidence law, or validated forensic-tool methodology.
