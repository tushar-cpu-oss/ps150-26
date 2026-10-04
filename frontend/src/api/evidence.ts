import { mediaUrl, request, uploadFile } from './client';
import { isR, list, toEvidence, toVerify } from './normalize';
import type { Evidence, VerifyResult } from '../types';

export async function listEvidence(caseId: string): Promise<Evidence[]> {
  return list(await request('/api/evidence', { query: { case_id: caseId } })).map(toEvidence);
}
export async function getEvidence(id: string): Promise<Evidence> {
  return toEvidence(await request(`/api/evidence/${id}`) as Record<string, unknown>);
}
export async function uploadEvidence(caseId: string, file: File, onProgress: (f: number) => void): Promise<Evidence> {
  const r = await uploadFile('/api/evidence/upload', { case_id: caseId }, file, onProgress);
  return toEvidence(isR(r) ? r : {});
}
export async function verifyEvidence(id: string): Promise<VerifyResult> {
  return toVerify(await request(`/api/evidence/${id}/verify`, { method: 'POST' }));
}
export const streamUrl = (id: string) => mediaUrl(`/api/evidence/${id}/stream`);
export const streamPath = (id: string) => `/api/evidence/${id}/stream`;
