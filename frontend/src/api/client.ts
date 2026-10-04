export const API_BASE = ((import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000').replace(/\/$/, '');
const KEY = 'rf.token';

export const tokenStore = {
  get: () => sessionStorage.getItem(KEY),
  set: (t: string) => sessionStorage.setItem(KEY, t),
  clear: () => sessionStorage.removeItem(KEY),
};

let onUnauthorized: (() => void) | null = null;
export const setUnauthorizedHandler = (fn: (() => void) | null) => { onUnauthorized = fn; };

export class ApiError extends Error {
  status: number; offline: boolean; detail?: unknown;
  constructor(message: string, status: number, offline = false, detail?: unknown) {
    super(message); this.status = status; this.offline = offline; this.detail = detail;
  }
}

function errMsg(d: unknown): string | undefined {
  if (d && typeof d === 'object' && 'error' in d) {
    const error = (d as { error?: unknown }).error;
    if (error && typeof error === 'object' && 'message' in error) return String((error as { message: unknown }).message);
  }
  if (d && typeof d === 'object' && 'detail' in d) {
    const x = (d as { detail: unknown }).detail;
    if (typeof x === 'string') return x;
    if (Array.isArray(x)) return x.map((i) => (i && typeof i === 'object' && 'msg' in i ? String((i as { msg: unknown }).msg) : String(i))).join('; ');
  }
  return undefined;
}

export function buildUrl(path: string, query?: Record<string, string | number | undefined>): string {
  const u = new URL(path.startsWith('http') ? path : `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`);
  if (query) for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== '') u.searchParams.set(k, String(v));
  return u.toString();
}

interface Opts { method?: string; json?: unknown; auth?: boolean; signal?: AbortSignal; query?: Record<string, string | number | undefined> }

export async function request<T = unknown>(path: string, o: Opts = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  const token = tokenStore.get();
  if (o.auth !== false && token) headers.Authorization = `Bearer ${token}`;
  let body: string | undefined;
  if (o.json !== undefined) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(o.json); }
  let res: Response;
  try {
    res = await fetch(buildUrl(path, o.query), { method: o.method ?? (body ? 'POST' : 'GET'), headers, body, signal: o.signal });
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw e;
    throw new ApiError('Unable to connect to Rocket Forensics API', 0, true);
  }
  if (!res.ok) {
    let detail: unknown;
    try { detail = await res.json(); } catch { /* not json */ }
    if (res.status === 401 && o.auth !== false) { tokenStore.clear(); onUnauthorized?.(); }
    throw new ApiError(errMsg(detail) ?? (res.statusText || 'Request failed'), res.status, false, detail);
  }
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get('content-type') ?? '';
  return (ct.includes('json') ? await res.json() : await res.text()) as T;
}

export function uploadFile<T = unknown>(
  path: string,
  fields: Record<string, string | undefined>,
  file: File,
  onProgress: (fraction: number) => void,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', buildUrl(path));
    const t = tokenStore.get();
    if (t) xhr.setRequestHeader('Authorization', `Bearer ${t}`);
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) onProgress(e.loaded / e.total); };
    xhr.onerror = () => reject(new ApiError('Unable to connect to Rocket Forensics API', 0, true));
    xhr.onload = () => {
      let parsed: unknown;
      try { parsed = JSON.parse(xhr.responseText); } catch { /* ignore */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(parsed as T);
      else {
        if (xhr.status === 401) { tokenStore.clear(); onUnauthorized?.(); }
        reject(new ApiError(errMsg(parsed) ?? 'Upload failed', xhr.status, false, parsed));
      }
    };
    const fd = new FormData();
    Object.entries(fields).forEach(([k, v]) => { if (v !== undefined && v !== '') fd.append(k, v); });
    fd.append('file', file);
    xhr.send(fd);
  });
}

/** Media endpoints authenticate with ?token= because <video>/<img> cannot set Authorization headers. */
export function mediaUrl(path: string): string {
  const t = tokenStore.get();
  return buildUrl(path, t ? { token: t } : undefined);
}

export async function fetchBlob(path: string): Promise<Blob> {
  const t = tokenStore.get();
  let res: Response;
  try { res = await fetch(buildUrl(path), { headers: t ? { Authorization: `Bearer ${t}` } : {} }); }
  catch { throw new ApiError('Unable to connect to Rocket Forensics API', 0, true); }
  if (!res.ok) throw new ApiError(res.statusText || 'Request failed', res.status);
  return res.blob();
}

export async function downloadFile(path: string, filename: string): Promise<void> {
  const blob = await fetchBlob(path);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

export async function pingBackend(): Promise<boolean> {
  try { const r = await fetch(`${API_BASE}/openapi.json`, { method: 'GET' }); return r.ok; } catch { return false; }
}
