import { ApiError, request } from './client';
import { isR, list, toAnalysis, toDetection, toMotion, toDevice, toEvidence } from './normalize';
import type { Analysis, Detection, DeviceFingerprint, Evidence, MotionEvent } from '../types';

export async function startAnalysis(evidenceId: string, objectTracking = false): Promise<{ analysis_id: string; status: string; existing?: boolean }> {
  let r: unknown;
  try {
    r = await request('/api/analysis/video', {
      method: 'POST',
      json: { evidence_id: evidenceId, options: { object_detection: true, motion_detection: true, face_detection: true, preset: 'balanced', object_tracking: objectTracking } },
    });
  } catch (e) {
    // 409 ANALYSIS_IN_PROGRESS: attach to the job that is already running instead of surfacing an error.
    if (e instanceof ApiError && e.status === 409) {
      const err = isR(e.detail) && isR(e.detail.error) ? e.detail.error : undefined;
      const det = err && isR(err.details) ? err.details : undefined;
      if (det && typeof det.analysis_id === 'string') {
        return { analysis_id: det.analysis_id, status: typeof det.status === 'string' ? det.status : 'processing', existing: true };
      }
    }
    throw e;
  }
  if (!isR(r) || typeof r.analysis_id !== 'string') throw new Error('Analysis response did not include analysis_id');
  return { analysis_id: r.analysis_id, status: typeof r.status === 'string' ? r.status : 'pending' };
}
export async function getAnalysis(analysisId: string): Promise<Analysis> {
  return toAnalysis(await request(`/api/analysis/${analysisId}`));
}
export async function getAnalysisForEvidence(evidence: Evidence): Promise<Analysis> {
  if (!evidence.latest_analysis_id) return toAnalysis({ status: evidence.analysis_status ?? 'not_started', evidence_id: evidence.id, case_id: evidence.case_id });
  return getAnalysis(evidence.latest_analysis_id);
}
export async function getDetectionsFromTimeline(caseId: string, evidenceId: string): Promise<Detection[]> {
  const raw = await request(`/api/timeline/${caseId}`, { query: { evidence_id: evidenceId, limit: 20000 } });
  return list(raw, 'events').filter((r) => String(r.event_type ?? '') === 'object_detection').map((r) => toDetection(r));
}
export async function getMotionEventsFromTimeline(caseId: string, evidenceId: string): Promise<MotionEvent[]> {
  const raw = await request(`/api/timeline/${caseId}`, { query: { evidence_id: evidenceId, limit: 20000 } });
  return list(raw, 'events').filter((r) => String(r.event_type ?? '') === 'motion').map(toMotion);
}
export async function getSnapshots(analysisId: string): Promise<Detection[]> {
  const raw = await request(`/api/analysis/${analysisId}/snapshots`);
  const out: Detection[] = [];
  for (const s of list(raw, 'snapshots')) {
    const timestamp = typeof s.timestamp === 'number' ? s.timestamp : 0;
    const frame = typeof s.frame_number === 'number' ? s.frame_number : undefined;
    const imageUrl = typeof s.image_url === 'string' ? s.image_url : undefined;
    const ds = Array.isArray(s.detections) ? s.detections.filter(isR) : [];
    for (const d of ds) {
      out.push(toDetection({ ...d, frame_number: frame, timestamp, image_url: imageUrl }));
    }
  }
  return out;
}
export async function getDevice(caseId: string, evidenceId: string): Promise<DeviceFingerprint | undefined> {
  const r = await request('/api/devices/detect', { method: 'POST', json: { case_id: caseId, evidence_id: evidenceId } });
  return toDevice(r);
}
