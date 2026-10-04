import { request } from './client';

export function acquireNetworkStream(body: { case_id: string; source_url: string; camera_id?: string; duration_seconds: number }) {
  return request('/api/acquisition/network', { method: 'POST', json: body });
}
