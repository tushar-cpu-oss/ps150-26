import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle, Loader2, WifiOff, X } from 'lucide-react';
import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { ApiError } from '../../api/client';

export function Panel({ title, right, children, className = '' }: { title?: string; right?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`panel ${className}`}>
      {(title || right) && (
        <header className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.06]">
          <h3 className="panel-title">{title}</h3>{right}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

type Tone = 'ice' | 'ok' | 'amber' | 'crit' | 'mute';
const TONES: Record<Tone, string> = {
  ice: 'text-ice border-ice/40 bg-ice/10', ok: 'text-ok border-ok/40 bg-ok/10', amber: 'text-amber border-amber/40 bg-amber/10',
  crit: 'text-crit border-crit/50 bg-crit/10', mute: 'text-slate-400 border-white/10 bg-white/[0.03]',
};
export function Badge({ tone = 'mute', children, dot = true }: { tone?: Tone; children: ReactNode; dot?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 border rounded-sm px-2 py-0.5 text-[10px] font-mono tracking-wider uppercase ${TONES[tone]}`}>
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}{children}
    </span>
  );
}

export function Button({ variant = 'primary', busy, children, ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'ghost' | 'danger'; busy?: boolean }) {
  return (
    <button {...p} disabled={p.disabled || busy} className={`btn-${variant} ${p.className ?? ''}`}>
      {busy && <Loader2 size={14} className="animate-spin" />}{children}
    </button>
  );
}

export function Modal({ open, title, onClose, children }: { open: boolean; title: string; onClose: () => void; children: ReactNode }) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onMouseDown={(e) => e.target === e.currentTarget && onClose()} role="dialog" aria-modal="true" aria-label={title}>
          <motion.div className="panel bg-panel w-full max-w-xl max-h-[90vh] overflow-auto" initial={{ y: 12, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 8, opacity: 0 }} transition={{ duration: 0.16 }}>
            <header className="flex items-center justify-between px-5 py-3 border-b border-white/[0.06]">
              <h2 className="panel-title">{title}</h2>
              <button onClick={onClose} aria-label="Close" className="text-slate-400 hover:text-cool"><X size={16} /></button>
            </header>
            <div className="p-5">{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function EmptyState({ title, text, action }: { title: string; text?: string; action?: ReactNode }) {
  return (
    <div className="panel border-dashed py-14 px-6 text-center">
      <p className="font-mono text-sm tracking-widest text-ice-dim">{title}</p>
      {text && <p className="mt-2 text-sm text-slate-400 max-w-md mx-auto">{text}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, title, text, onRetry }: { error?: unknown; title?: string; text?: string; onRetry?: () => void }) {
  const offline = error instanceof ApiError && error.offline;
  const status = error instanceof ApiError ? error.status : undefined;
  const t = offline ? 'BACKEND OFFLINE' : title ?? 'REQUEST FAILED';
  const body = offline ? 'Unable to connect to Rocket Forensics API. Check that the backend is running and VITE_API_BASE_URL is correct.' : text ?? (error instanceof Error ? error.message : 'Something went wrong.');
  return (
    <div className="panel border-crit/30 py-10 px-6 text-center">
      {offline ? <WifiOff className="mx-auto text-crit" size={22} /> : <AlertTriangle className="mx-auto text-amber" size={22} />}
      <p className="mt-3 font-mono text-sm tracking-widest text-cool">{t}</p>
      <p className="mt-2 text-sm text-slate-400 max-w-md mx-auto">{body}</p>
      {status ? <p className="mt-1 text-[11px] font-mono text-slate-500">HTTP {status}</p> : null}
      {onRetry && <div className="mt-4"><Button variant="ghost" onClick={onRetry}>{offline ? 'Retry connection' : 'Retry'}</Button></div>}
    </div>
  );
}

/** Shows real progress only when a fraction (0..1) is supplied; otherwise an indeterminate bar. */
export function LoadingState({ label = 'PROCESSING…', progress, compact }: { label?: string; progress?: number; compact?: boolean }) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 ${compact ? 'py-6' : 'py-20'}`} role="status">
      <p className="font-mono text-xs tracking-[0.2em] text-ice-dim">{label}</p>
      <div className="h-1 w-56 bg-white/[0.06] rounded overflow-hidden">
        {progress === undefined
          ? <motion.div className="h-full w-1/3 bg-ice/70" animate={{ x: ['-100%', '300%'] }} transition={{ repeat: Infinity, duration: 1.4, ease: 'linear' }} />
          : <div className="h-full bg-ice" style={{ width: `${Math.round(progress * 100)}%` }} />}
      </div>
    </div>
  );
}

export function KV({ k, v, mono }: { k: string; v: ReactNode; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-4 py-1.5 border-b border-white/[0.04] last:border-0 text-sm">
      <span className="text-slate-500">{k}</span>
      <span className={`text-right ${mono ? 'font-mono text-xs' : ''}`}>{v}</span>
    </div>
  );
}
