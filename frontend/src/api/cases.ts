import { request } from './client';
import { isR, list, toCase } from './normalize';
import type { Case } from '../types';

export async function listCases(): Promise<Case[]> { return list(await request('/api/cases')).map(toCase); }
export async function getCase(id: string): Promise<Case> { return toCase(await request(`/api/cases/${id}`) as Record<string, unknown>); }
export async function createCase(p: { case_number: string; title: string; description: string }): Promise<Case> {
  // The UI keeps CASE NUMBER/TITLE fields. The backend contract uses name/description and generates case_number.
  const r = await request('/api/cases', { method: 'POST', json: { name: p.title, description: p.description } });
  return toCase(isR(r) ? r : {});
}
