export function fmtClock(sec?: number | null): string {
  if (sec == null || !Number.isFinite(sec)) return '--:--:--';
  const s = Math.max(0, Math.floor(sec));
  return [Math.floor(s / 3600), Math.floor((s % 3600) / 60), s % 60].map((n) => String(n).padStart(2, '0')).join(':');
}
export function fmtBytes(n?: number): string {
  if (n == null) return '—';
  const u = ['B', 'KB', 'MB', 'GB', 'TB']; let i = 0; let v = n;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(i ? 1 : 0)} ${u[i]}`;
}
export function fmtDate(iso?: string): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
}
export const shortHash = (h?: string, n = 8) => (!h ? '—' : h.length <= n * 2 ? h : `${h.slice(0, n)}…${h.slice(-4)}`);
export const evidenceLabel = (id: string) => `EVIDENCE-${id.slice(-5).toUpperCase()}`;
export function pct(c?: number): string {
  if (c == null) return '—';
  return `${Math.round(c <= 1 ? c * 100 : c)}%`;
}
export const fmtRes = (w?: number, h?: number) => (w && h ? `${w} × ${h}` : '—');
