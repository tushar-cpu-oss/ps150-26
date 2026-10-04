import { request } from './client';
import { list, toCorrelationGroup, toTimelineEvent } from './normalize';
import type { CorrelationResult, TimelineEvent } from '../types';

export async function caseTimeline(caseId: string): Promise<TimelineEvent[]> {
  return list(await request(`/api/timeline/${caseId}`, { query: { limit: 20000 } }), 'events').map(toTimelineEvent);
}
export async function caseCorrelation(caseId: string): Promise<CorrelationResult> {
  const raw = await request(`/api/timeline/${caseId}/correlation`);
  const r = (raw && typeof raw === 'object') ? raw as Record<string, unknown> : {};
  return { count: typeof r.count === 'number' ? r.count : 0, disclaimer: typeof r.disclaimer === 'string' ? r.disclaimer : 'NO DATA AVAILABLE',
    groups: list(raw, 'groups').map(toCorrelationGroup) };
}
