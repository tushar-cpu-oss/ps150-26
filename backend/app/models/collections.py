"""Document shapes stored in MongoDB (documented here; validated by schemas/).

users:            user_id, full_name, email, organization, password_hash, role, created_at, updated_at
cases:            case_id, case_number, name, description, investigator, investigator_id, status, created_at, updated_at
evidence:         evidence_id, case_id, original_filename, stored_filename, storage_path,
                  extension, mime_type, file_size, camera_id, recording_start,
                  recording_start_source, md5, sha256, hash_algorithm, hashed_at,
                  metadata, metadata_error, processing_status, analysis_status,
                  latest_analysis_id, last_verified_at, last_verification_passed, uploaded_by, created_at
devices:          device_id, case_id, evidence_id, manufacturer, model, serial_number, firmware,
                  channels, source, confidence, confidence_basis, note, created_at
analysis_jobs:    analysis_id, case_id, evidence_id, status, options, progress, modules, warnings,
                  counts, error, created_at, started_at, completed_at
detections:       detection_id, analysis_id, case_id, evidence_id, timestamp, video_time_seconds,
                  frame_number, class_name, class_id, confidence, bbox{x1,y1,x2,y2}, created_at
timeline_events:  event_id, case_id, evidence_id, analysis_id, timestamp, video_time_seconds,
                  event_type, class_name, confidence, frame_number, camera_id, motion_score,
                  detection_id, metadata
chain_of_custody: custody_id, case_id, evidence_id, action, actor (name), actor_user_id, timestamp, sha256, description
reports:          report_id, case_id, evidence_ids, filename, sha256, file_size, generated_at, generated_by
counters:         internal sequence generator (not exposed)
"""
CASE_STATUSES = ("active", "archived", "closed")
CUSTODY_ACTIONS = ("EVIDENCE_ACQUIRED", "HASH_GENERATED", "EVIDENCE_VERIFIED",
                   "ANALYSIS_STARTED", "ANALYSIS_COMPLETED", "REPORT_GENERATED")
VENDORS = ("Dahua", "CP Plus", "Honeywell", "TP-Link", "Godrej", "Uniview", "Hikvision", "Matrix", "Unknown")
