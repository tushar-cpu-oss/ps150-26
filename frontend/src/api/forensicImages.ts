import { request, uploadFile } from './client';

export interface ForensicImage {
  image_id: string; case_id: string; filename: string; image_type?: string; size_bytes: number;
  md5: string; sha256: string; parser_status: string; created_at: string;
}

export async function ingestForensicImage(caseId: string, file: File, onProgress: (f: number) => void): Promise<ForensicImage> {
  return uploadFile('/api/forensic-images/ingest', { case_id: caseId }, file, onProgress) as Promise<ForensicImage>;
}
export async function inspectForensicImage(id: string): Promise<Record<string, unknown>> {
  return request(`/api/forensic-images/${id}/inspect`);
}
export async function recoverStandardArtifacts(id: string, maxItems = 100): Promise<Record<string, unknown>> {
  return request(`/api/forensic-images/${id}/recover`, { method: 'POST', json: { image_id: id, max_items: maxItems } });
}
