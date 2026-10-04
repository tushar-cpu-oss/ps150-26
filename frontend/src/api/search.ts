import { request } from './client';
import { list, toTimelineEvent } from './normalize';
import type { TimelineEvent } from '../types';

export interface SearchParams {
  object?: string; camera?: string; from?: string; to?: string; min_confidence?: string; evidence_id?: string; limit?: string;
}
export async function searchCase(caseId: string, p: SearchParams): Promise<TimelineEvent[]> {
  return list(await request('/api/search', { query: { case_id: caseId, ...p } }), 'results').map(toTimelineEvent);
}
