export interface User {
  id: string; full_name: string; email: string; organization?: string; role?: string; created_at?: string; updated_at?: string;
}
export interface Case {
  id: string; case_number: string; title: string; description?: string; investigator?: string; investigator_id?: string;
  status: string; evidence_count?: number; event_count?: number; created_at?: string; updated_at?: string;
}
export interface DeviceFingerprint {
  vendor?: string; model?: string; method?: string; confidence?: string; known: boolean; confidence_basis?: string;
}
export type IntegrityState = 'verified' | 'failed' | 'pending';
export interface Evidence {
  id: string; case_id: string; filename: string; file_size?: number; sha256?: string; md5?: string;
  media_type?: string; extension?: string; width?: number; height?: number; fps?: number; duration?: number; codec?: string;
  acquired_at?: string; created_at?: string; recording_start?: string; metadata?: Record<string, unknown>;
  metadata_error?: string; processing_status?: string; integrity: IntegrityState; analysis_status?: string;
  latest_analysis_id?: string; camera_id?: string; device?: DeviceFingerprint;
}
export interface VerifyResult {
  state: IntegrityState; sha256Match?: boolean; md5Match?: boolean; sha256?: string; md5?: string;
  storedSha256?: string; storedMd5?: string; currentSha256?: string; currentMd5?: string; checked_at?: string; message?: string;
}
export type AnalysisState = 'not_started' | 'pending' | 'processing' | 'completed' | 'failed';
export interface AnalysisStage { name: string; status: 'pending' | 'running' | 'completed' | 'skipped' | 'failed' }
export interface Analysis {
  analysis_id?: string; case_id?: string; evidence_id?: string; state: AnalysisState; rawStatus?: string;
  options?: Record<string, unknown>; model?: string; model_version?: string; snapshots?: number; progress?: number;
  stage?: string; stages?: AnalysisStage[];
  modules?: Record<string, unknown>; warnings?: string[]; counts?: Record<string, number>; error?: string;
  created_at?: string; started_at?: string; completed_at?: string;
}
export interface BBox { x1: number; y1: number; x2: number; y2: number }
export type DetectionCategory = 'person' | 'vehicle' | 'object';
export interface Detection {
  id: string; label: string; category: DetectionCategory; confidence?: number; timestamp: number; track_id?: number;
  frame?: number; bbox?: BBox; snapshot_url?: string; evidence_id?: string;
}
export interface MotionEvent { id: string; start: number; end: number; duration: number; evidence_id?: string; }
export interface TimelineEvent {
  id: string; type: string; label: string; timestamp: number; wallClock?: string; camera?: string;
  confidence?: number; evidence_id?: string; frame?: number; analysis_id?: string; motion_score?: number;
}
export interface CorrelationEvent {
  event_id: string; camera_id?: string; timestamp?: string; evidence_id?: string; video_time_seconds?: number; confidence?: number;
}
export interface CorrelationResult { count: number; disclaimer: string; groups: CorrelationGroup[]; }
export interface CorrelationGroup {
  group_id: string; class_name: string; cameras: string[]; start_time?: string; end_time?: string;
  window_seconds: number; event_count: number; label?: string; events: CorrelationEvent[];
}
export interface ChainOfCustodyEvent {
  id: string; actor: string; actor_name?: string; action: string; timestamp?: string; evidence_id?: string;
  sha256?: string; description?: string;
}
export interface ForensicReport {
  id: string; case_id?: string; evidence_ids?: string[]; filename?: string; sha256?: string; file_size?: number;
  generated_by?: string; generated_at?: string; download_url?: string;
}
