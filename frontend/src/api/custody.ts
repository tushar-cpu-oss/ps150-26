import { request } from './client';
import { list, toCustody } from './normalize';
import type { ChainOfCustodyEvent, Evidence } from '../types';

export async function evidenceCustody(evidenceId: string): Promise<ChainOfCustodyEvent[]> {
  return list(await request(`/api/chain-of-custody/${evidenceId}`), 'records').map(toCustody);
}
export async function caseCustody(evidence: Evidence[]): Promise<ChainOfCustodyEvent[]> {
  const results = await Promise.all(evidence.map((e) => evidenceCustody(e.id)));
  return results.flat().sort((a, b) => String(a.timestamp ?? '').localeCompare(String(b.timestamp ?? '')));
}
