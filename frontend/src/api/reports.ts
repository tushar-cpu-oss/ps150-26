import { downloadFile, request } from './client';
import { isR, toReport } from './normalize';
import type { ForensicReport } from '../types';

export async function generateReport(caseId: string, evidenceIds?: string[]): Promise<ForensicReport> {
  const r = await request('/api/reports/generate', { method: 'POST', json: { case_id: caseId, ...(evidenceIds ? { evidence_ids: evidenceIds } : {}) } });
  return toReport(isR(r) ? r : {});
}
export async function getReport(id: string): Promise<ForensicReport> {
  return toReport(await request(`/api/reports/${id}`) as Record<string, unknown>);
}
export const downloadReport = (id: string) => downloadFile(`/api/reports/${id}/download`, `rocket-forensics-report-${id}.pdf`);
