import { Link } from 'react-router-dom';
import { useState } from 'react';
import { verifyEvidence } from '../../api/evidence';
import { startAnalysis } from '../../api/analysis';
import { useToast } from '../../context/ToastContext';
import { evidenceLabel, fmtClock, fmtRes, shortHash } from '../../lib/format';
import type { Evidence } from '../../types';
import { Button } from '../common/ui';
import { IntegrityBadge } from './EvidenceIntegrity';

export default function EvidenceCard({ e, onChanged }: { e: Evidence; onChanged: () => void }) {
  const toast = useToast();
  const [busy, setBusy] = useState<'v' | 'a' | null>(null);
  const verify = async () => {
    setBusy('v');
    try { const r = await verifyEvidence(e.id); toast(r.state === 'failed' ? 'critical' : 'success', r.state === 'failed' ? 'Integrity mismatch detected' : 'Hash verified'); onChanged(); }
    catch (x) { toast('critical', x instanceof Error ? x.message : 'Verification failed'); } finally { setBusy(null); }
  };
  const analyze = async () => {
    setBusy('a');
    try { await startAnalysis(e.id); toast('info', 'Analysis started'); onChanged(); }
    catch (x) { toast('critical', x instanceof Error ? x.message : 'Analysis failed'); } finally { setBusy(null); }
  };
  return (
    <article className="panel p-4 flex flex-col gap-3 hover:border-ice/30 transition-colors">
      <div>
        <p className="font-mono text-[11px] text-ice tracking-wider">{evidenceLabel(e.id)}</p>
        <h3 className="text-sm font-medium truncate" title={e.filename}>{e.filename}</h3>
      </div>
      <div className="font-mono text-[11px] text-slate-400 space-y-0.5">
        <p>{(e.media_type ?? 'VIDEO').toUpperCase()}</p>
        <p>{fmtRes(e.width, e.height)}{e.fps ? ` · ${e.fps.toFixed(2)} FPS` : ''}</p>
        <p>{e.duration != null ? fmtClock(e.duration) : '—'}</p>
      </div>
      <div>
        <p className="panel-title">SHA-256</p>
        <p className="mono text-xs mt-0.5" title={e.sha256}>{shortHash(e.sha256)}</p>
      </div>
      <div className="flex items-center justify-between">
        <IntegrityBadge state={e.integrity} />
        {e.analysis_status && <span className="text-[10px] font-mono tracking-wider text-slate-500">ANALYSIS · {e.analysis_status.toUpperCase()}</span>}
      </div>
      <div className="flex gap-2 pt-1">
        <Link to={`/evidence/${e.id}`} className="btn-primary flex-1">OPEN</Link>
        <Button variant="ghost" busy={busy === 'v'} onClick={verify}>VERIFY</Button>
        <Button variant="ghost" busy={busy === 'a'} onClick={analyze}>ANALYZE</Button>
      </div>
    </article>
  );
}
