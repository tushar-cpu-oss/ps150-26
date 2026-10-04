import { useState } from 'react';
import { CheckCircle2, Copy, ShieldAlert, ShieldQuestion } from 'lucide-react';
import { verifyEvidence } from '../../api/evidence';
import { useToast } from '../../context/ToastContext';
import type { Evidence, IntegrityState, VerifyResult } from '../../types';
import { Button, Panel } from '../common/ui';

export function IntegrityBadge({ state }: { state: IntegrityState }) {
  const m = { verified: ['text-ok', 'VERIFIED', CheckCircle2], failed: ['text-crit', 'INTEGRITY FAILURE', ShieldAlert], pending: ['text-slate-400', 'NOT VERIFIED', ShieldQuestion] } as const;
  const [cls, label, Icon] = m[state];
  return <span className={`inline-flex items-center gap-1.5 text-[11px] font-mono tracking-wider ${cls}`}><Icon size={13} />{label}</span>;
}

function HashRow({ label, hash, state }: { label: string; hash?: string; state: IntegrityState }) {
  const toast = useToast();
  return (
    <div className="py-3 border-b border-white/[0.05] last:border-0">
      <div className="flex items-center justify-between">
        <span className="panel-title">{label}</span><IntegrityBadge state={state} />
      </div>
      <div className="mt-2 flex items-start gap-2">
        <p className="mono text-[13px] break-all text-cool leading-relaxed flex-1">{hash ?? 'NO DATA AVAILABLE'}</p>
        {hash && <button aria-label={`Copy ${label}`} className="text-slate-500 hover:text-ice" onClick={() => { void navigator.clipboard.writeText(hash); toast('info', `${label} copied`); }}><Copy size={14} /></button>}
      </div>
    </div>
  );
}

export default function EvidenceIntegrity({ evidence, onChange }: { evidence: Evidence; onChange?: () => void }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<VerifyResult | null>(null);
  const overall = res?.state ?? evidence.integrity;
  const sha = res?.sha256Match === undefined ? overall : res.sha256Match ? 'verified' : 'failed';
  const md5 = res?.md5Match === undefined ? overall : res.md5Match ? 'verified' : 'failed';

  const run = async () => {
    setBusy(true);
    try {
      const r = await verifyEvidence(evidence.id);
      setRes(r);
      if (r.state === 'failed') toast('critical', 'Integrity mismatch detected');
      else if (r.state === 'verified') toast('success', 'Hash verified');
      onChange?.();
    } catch (e) { toast('critical', e instanceof Error ? e.message : 'Verification failed'); }
    finally { setBusy(false); }
  };
  return (
    <Panel title="EVIDENCE INTEGRITY" right={<Button variant="ghost" busy={busy} onClick={run}>VERIFY AGAIN</Button>}>
      <HashRow label="SHA-256" hash={evidence.sha256} state={sha} />
      <HashRow label="MD5" hash={evidence.md5} state={md5} />
      {res?.state === 'verified' && <p className="mt-3 text-xs font-mono tracking-wider text-ok">HASH MATCH · FILE INTEGRITY CONFIRMED</p>}
      {res?.state === 'failed' && <p className="mt-3 text-xs font-mono tracking-wider text-crit border border-crit/40 bg-crit/10 rounded px-3 py-2">INTEGRITY FAILURE · HASH MISMATCH DETECTED</p>}
      {res?.checked_at && <p className="mt-2 text-[11px] font-mono text-slate-500">CHECKED {res.checked_at}</p>}
    </Panel>
  );
}
