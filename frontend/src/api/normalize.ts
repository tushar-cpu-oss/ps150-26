import type {
  Analysis, AnalysisStage, AnalysisState, BBox, Case, ChainOfCustodyEvent, CorrelationEvent, CorrelationGroup, Detection,
  DetectionCategory, DeviceFingerprint, Evidence, ForensicReport, IntegrityState, MotionEvent, TimelineEvent, User, VerifyResult,
} from '../types';

export type R = Record<string, unknown>;
export const isR = (v: unknown): v is R => typeof v === 'object' && v !== null && !Array.isArray(v);
export function pick(o: R, ...keys: string[]): unknown {
  for (const k of keys) { const v = o[k]; if (v !== undefined && v !== null) return v; }
  return undefined;
}
export const str = (v: unknown): string | undefined => (v === undefined || v === null || v === '' ? undefined : String(v));
export const num = (v: unknown): number | undefined => {
  const n = typeof v === 'number' ? v : typeof v === 'string' && v.trim() !== '' ? Number(v) : NaN;
  return Number.isFinite(n) ? n : undefined;
};
export function list(raw: unknown, ...keys: string[]): R[] {
  if (Array.isArray(raw)) return raw.filter(isR);
  if (isR(raw)) for (const k of [...keys, 'items', 'results', 'data']) {
    const v = raw[k]; if (Array.isArray(v)) return v.filter(isR);
  }
  return [];
}
const id = (o: R) => str(pick(o, 'id', '_id', 'evidence_id', 'case_id', 'report_id', 'event_id', 'analysis_id')) ?? '';

export function toSeconds(v: unknown): number | undefined {
  const n = num(v); if (n !== undefined) return n;
  if (typeof v === 'string' && /^\d+:\d{2}(:\d{2})?(\.\d+)?$/.test(v)) return v.split(':').map(Number).reduce((a, b) => a * 60 + b, 0);
  return undefined;
}
export function toUser(r: R): User {
  return {
    id: str(r.user_id) ?? id(r), full_name: str(r.full_name) ?? 'Investigator', email: str(r.email) ?? '',
    organization: str(r.organization), role: str(r.role), created_at: str(r.created_at), updated_at: str(r.updated_at)
  };
}
export function toCase(r: R): Case {
  return {
    id: str(r.case_id) ?? id(r), case_number: str(r.case_number) ?? 'NO DATA AVAILABLE', title: str(r.name) ?? 'Untitled case',
    description: str(r.description), investigator: str(r.investigator), investigator_id: str(r.investigator_id), status: (str(r.status) ?? 'active').toUpperCase(),
    evidence_count: num(r.evidence_count), event_count: num(r.event_count), created_at: str(r.created_at), updated_at: str(r.updated_at)
  };
}
export function toDevice(v: unknown): DeviceFingerprint | undefined {
  if (!isR(v)) return undefined;
  const manufacturer = str(v.manufacturer);
  const known = !!manufacturer && manufacturer.toLowerCase() !== 'unknown';
  return {
    vendor: manufacturer, model: str(v.model), method: str(v.identification_method),
    confidence: str(v.confidence), known, confidence_basis: str(v.confidence_basis)
  };
}
function integrityOf(v: unknown): IntegrityState {
  const s = String(v ?? '').toLowerCase();
  if (v === true || ['verified', 'match', 'ok', 'valid', 'passed'].includes(s)) return 'verified';
  if (v === false || ['failed', 'mismatch', 'tampered', 'invalid'].includes(s)) return 'failed';
  return 'pending';
}
export function toEvidence(r: R): Evidence {
  const meta = isR(r.metadata) ? r.metadata : {};
  const duration = num(meta.duration ?? meta.duration_seconds);
  return {
    id: str(r.evidence_id) ?? id(r), case_id: str(r.case_id) ?? '', filename: str(r.original_filename) ?? 'unnamed',
    file_size: num(r.file_size), sha256: str(r.sha256), md5: str(r.md5), media_type: str(r.mime_type), extension: str(r.extension),
    width: num(meta.width), height: num(meta.height), fps: num(meta.fps ?? meta.frame_rate), duration,
    codec: str(meta.codec ?? meta.video_codec), acquired_at: str(r.created_at), created_at: str(r.created_at),
    recording_start: str(r.recording_start), metadata: meta, metadata_error: str(r.metadata_error), processing_status: str(r.processing_status),
    integrity: integrityOf(r.last_verification_passed), analysis_status: str(r.analysis_status), latest_analysis_id: str(r.latest_analysis_id),
    camera_id: str(r.camera_id)
  };
}
export function toVerify(raw: unknown): VerifyResult {
  const r = isR(raw) ? raw : {};
  return {
    state: integrityOf(r.verified), sha256Match: typeof r.stored_sha256 === 'string' && typeof r.current_sha256 === 'string' ? r.stored_sha256 === r.current_sha256 : undefined,
    md5Match: typeof r.stored_md5 === 'string' && typeof r.current_md5 === 'string' ? r.stored_md5 === r.current_md5 : undefined,
    sha256: str(r.current_sha256), md5: str(r.current_md5), storedSha256: str(r.stored_sha256), storedMd5: str(r.stored_md5),
    currentSha256: str(r.current_sha256), currentMd5: str(r.current_md5), checked_at: str(r.verified_at), message: str(r.message)
  };
}
export function toAnalysis(raw: unknown): Analysis {
  const r = isR(raw) ? raw : {};
  const s = (str(r.status) ?? 'not_started').toLowerCase();
  const state: AnalysisState = s === 'queued' || s === 'pending' ? 'pending' : s === 'processing' ? 'processing' :
    s === 'completed' ? 'completed' : s === 'failed' ? 'failed' : 'not_started';
  return {
    analysis_id: str(r.analysis_id), case_id: str(r.case_id), evidence_id: str(r.evidence_id), state, rawStatus: s,
    options: isR(r.options) ? r.options : undefined, model: str(r.model), model_version: str(r.model_version), snapshots: num(r.snapshots),
    progress: num(r.progress), stage: str(r.stage),
    stages: Array.isArray(r.stages) ? r.stages.filter(isR).map((x) => ({ name: str(x.name) ?? '', status: (str(x.status) ?? 'pending') as AnalysisStage['status'] })).filter((x) => x.name) : [],
    modules: isR(r.modules) ? r.modules : {}, warnings: Array.isArray(r.warnings) ? r.warnings.filter((x): x is string => typeof x === 'string') : [],
    counts: isR(r.counts) ? Object.fromEntries(Object.entries(r.counts).filter(([, v]) => typeof v === 'number') as [string, number][]) : {},
    error: str(r.error), created_at: str(r.created_at), started_at: str(r.started_at), completed_at: str(r.completed_at)
  };
}
export function categoryOf(label: string): DetectionCategory {
  const l = label.toLowerCase(); if (l === 'person') return 'person';
  if (['car', 'truck', 'bus', 'motorcycle', 'bicycle', 'vehicle', 'van'].includes(l)) return 'vehicle'; return 'object';
}
function toBox(v: unknown): BBox | undefined {
  if (Array.isArray(v) && v.length >= 4) { const [a, b, c, d] = v.map(Number); if ([a, b, c, d].every(Number.isFinite)) return { x1: a, y1: b, x2: c, y2: d }; }
  if (isR(v)) { const x1 = num(v.x1), y1 = num(v.y1), x2 = num(v.x2), y2 = num(v.y2); if ([x1, y1, x2, y2].every((x) => x !== undefined)) return { x1: x1!, y1: y1!, x2: x2!, y2: y2! }; }
  return undefined;
}
export function toDetection(r: R): Detection {
  const label = str(r.class_name) ?? str(r.event_type) ?? 'object';
  const ts = num(r.video_time_seconds ?? r.timestamp) ?? 0;
  return {
    id: (str(r.detection_id) ?? str(r.event_id) ?? id(r) ?? `${label}-${ts}`), label, category: categoryOf(label),
    confidence: num(r.confidence), timestamp: ts, track_id: num(r.track_id) ?? (isR(r.metadata) ? num(r.metadata.track_id) : undefined), frame: num(r.frame_number), bbox: toBox(r.bbox), snapshot_url: str(r.image_url ?? r.snapshot_url), evidence_id: str(r.evidence_id)
  };
}
export function toMotion(r: R): MotionEvent {
  const ts = num(r.video_time_seconds) ?? 0; return { id: (str(r.event_id) ?? id(r) ?? `motion-${ts}`), start: ts, end: ts, duration: 0, evidence_id: str(r.evidence_id) };
}
export function toTimelineEvent(r: R): TimelineEvent {
  const type = str(r.event_type) ?? 'event'; const ts = num(r.video_time_seconds) ?? 0;
  return {
    id: str(r.event_id) ?? id(r), type: type.toLowerCase(), label: str(r.class_name) ?? str(isR(r.metadata) ? r.metadata.description : undefined) ?? type,
    timestamp: ts, wallClock: str(r.timestamp), camera: str(r.camera_id), confidence: num(r.confidence), evidence_id: str(r.evidence_id),
    frame: num(r.frame_number), analysis_id: str(r.analysis_id), motion_score: num(r.motion_score)
  };
}
function toCorrelationEvent(v: unknown): CorrelationEvent {
  const r = isR(v) ? v : {}; return {
    event_id: str(r.event_id) ?? '', camera_id: str(r.camera_id), timestamp: str(r.timestamp),
    evidence_id: str(r.evidence_id), video_time_seconds: num(r.video_time_seconds), confidence: num(r.confidence)
  };
}
export function toCorrelationGroup(r: R): CorrelationGroup {
  return {
    group_id: str(r.group_id) ?? id(r), class_name: str(r.class_name) ?? 'object', cameras: Array.isArray(r.cameras) ? r.cameras.filter((x): x is string => typeof x === 'string') : [],
    start_time: str(r.start_time), end_time: str(r.end_time), window_seconds: num(r.window_seconds) ?? 0, event_count: num(r.event_count) ?? 0,
    label: str(r.label), events: Array.isArray(r.events) ? r.events.map(toCorrelationEvent) : []
  };
}
export function toCustody(r: R): ChainOfCustodyEvent {
  return {
    id: str(r.custody_id) ?? id(r), actor: str(r.actor) ?? 'system', actor_name: str(r.actor_name), action: str(r.action) ?? 'EVENT',
    timestamp: str(r.timestamp), evidence_id: str(r.evidence_id), sha256: str(r.sha256), description: str(r.description)
  };
}
export function toReport(r: R): ForensicReport {
  return {
    id: str(r.report_id) ?? id(r), case_id: str(r.case_id), evidence_ids: Array.isArray(r.evidence_ids) ? r.evidence_ids.filter((x): x is string => typeof x === 'string') : [],
    filename: str(r.filename), sha256: str(r.sha256), file_size: num(r.file_size), generated_by: str(r.generated_by), generated_at: str(r.generated_at), download_url: str(r.download_url)
  };
}
