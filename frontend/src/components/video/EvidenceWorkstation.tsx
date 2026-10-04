import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { X } from 'lucide-react';
import { mediaUrl } from '../../api/client';
import { getAnalysis, getAnalysisForEvidence, getDetectionsFromTimeline, getMotionEventsFromTimeline, getSnapshots, startAnalysis } from '../../api/analysis';
import { useAsync } from '../../hooks/useAsync';
import { useToast } from '../../context/ToastContext';
import { fmtClock, pct } from '../../lib/format';
import type { Analysis, Detection, DetectionCategory, Evidence, MotionEvent } from '../../types';
import { Badge, Button, EmptyState, ErrorState, LoadingState, Panel } from '../common/ui';
import ForensicVideoPlayer, { type PlayerHandle } from './ForensicVideoPlayer';
import VideoTimeline from './VideoTimeline';

function AnalysisStatus({ a, onStart, busy }: { a: Analysis; onStart: () => void; busy: boolean }) {
  const running = a.state === 'processing' || a.state === 'pending';
  const tone = a.state === 'completed' ? 'ok' : a.state === 'failed' ? 'crit' : running ? 'ice' : 'mute';
  const label = { not_started: 'NOT STARTED', pending: 'QUEUED', processing: 'PROCESSING', completed: 'ANALYSIS COMPLETE', failed: 'ANALYSIS FAILED' }[a.state];
  return (
    <Panel title="ANALYSIS" right={<Badge tone={tone}>{label}</Badge>}>
      {running && a.progress != null && (
        <div className="mt-2"><LoadingState compact label={`PROCESSING ${Math.round(a.progress * 100)}%`} progress={a.progress} /></div>
      )}
      {a.stages && a.stages.length > 0 && (
        <ol className="mt-2 space-y-1 text-xs font-mono" aria-label="Analysis stages">
          {a.stages.map((st) => (
            <li key={st.name} className={st.status === 'running' ? 'text-ice' : st.status === 'failed' ? 'text-crit' : st.status === 'completed' ? 'text-cool' : 'text-slate-500'}>
              {st.name.replace(/_/g, ' ').toUpperCase()} · {st.status.toUpperCase()}
            </li>
          ))}
        </ol>
      )}
      {a.model && <p className="mono text-xs text-slate-500 mt-2">MODEL · {a.model}{a.model_version ? ` · ${a.model_version}` : ''}</p>}
      {a.modules && Object.keys(a.modules).length > 0 && (
        <div className="mt-2 grid grid-cols-2 gap-2 text-xs font-mono">
          {Object.entries(a.modules).map(([k, v]) => <div key={k}><p className="panel-title">{k.replace(/_/g, ' ').toUpperCase()}</p><p className="text-cool">{String(v).toUpperCase()}</p></div>)}
        </div>
      )}
      {a.warnings?.length ? <div className="mt-3 text-xs text-slate-400"><p className="panel-title">WARNINGS</p>{a.warnings.map((w) => <p key={w} className="mt-1">{w}</p>)}</div> : null}
      {a.counts && Object.keys(a.counts).length > 0 && <p className="mono text-xs text-slate-500 mt-2">{Object.entries(a.counts).map(([k,v]) => `${k}=${v}`).join(' · ')}</p>}
      {a.state === 'failed' && <div className="mt-2"><ErrorState title="ANALYSIS FAILED" /><details className="mt-2 text-xs text-slate-500"><summary className="cursor-pointer">View technical details</summary><p className="mono mt-1">{a.error ?? 'NO DATA AVAILABLE'}</p></details></div>}
      {(a.state === 'not_started' || a.state === 'failed' || a.state === 'completed') && <div className="mt-3"><Button variant={a.state === 'completed' ? 'ghost' : 'primary'} busy={busy} onClick={onStart}>{a.state === 'completed' ? 'RE-RUN ANALYSIS' : 'START ANALYSIS'}</Button></div>}
    </Panel>
  );
}
const TABS: { id: DetectionCategory | 'motion'; label: string }[] = [
  { id: 'person', label: 'PERSON DET.' }, { id: 'vehicle', label: 'VEHICLES' }, { id: 'object', label: 'OBJECTS' }, { id: 'motion', label: 'MOTION' },
];

export default function EvidenceWorkstation({ evidence }: { evidence: Evidence }) {
  const toast = useToast();
  const [params] = useSearchParams();
  const t0 = Number(params.get('t')) || undefined;
  const player = useRef<PlayerHandle>(null);
  const [cur, setCur] = useState(0); const [dur, setDur] = useState(evidence.duration ?? 0);
  const [sel, setSel] = useState<Detection | null>(null); const [tab, setTab] = useState<DetectionCategory | 'motion'>('person');
  const [preview, setPreview] = useState<Detection | null>(null); const [starting, setStarting] = useState(false);
  // latest_analysis_id on the evidence record is only set when a job COMPLETES, so a running job
  // must be tracked locally (set after start, or after a 409 that names the running job).
  const [activeId, setActiveId] = useState<string | null>(null);
  const [tracking, setTracking] = useState(false);
  const analysis = useAsync(() => activeId ? getAnalysis(activeId) : getAnalysisForEvidence(evidence), [evidence, activeId]);
  const state = analysis.data?.state;
  useEffect(() => {
    if (state !== 'processing' && state !== 'pending') return;
    const t = setInterval(analysis.reload, 3000); return () => clearInterval(t);
  }, [state, analysis.reload]);
  const prev = useRef<string | undefined>();
  useEffect(() => { if (prev.current && prev.current !== state && state === 'completed') toast('success', 'Analysis completed'); prev.current = state; }, [state, toast]);
  const ready = state === 'completed';
  const det = useAsync(() => ready ? getDetectionsFromTimeline(evidence.case_id, evidence.id) : Promise.resolve([]), [evidence.case_id, evidence.id, ready]);
  const mot = useAsync(() => ready ? getMotionEventsFromTimeline(evidence.case_id, evidence.id) : Promise.resolve([]), [evidence.case_id, evidence.id, ready]);
  const doneId = analysis.data?.analysis_id || evidence.latest_analysis_id;
  const snaps = useAsync(() => ready && doneId ? getSnapshots(doneId) : Promise.resolve([]), [doneId, ready]);
  const start = async () => {
    setStarting(true);
    try {
      const r = await startAnalysis(evidence.id, tracking);
      setActiveId(r.analysis_id);
      toast('info', r.existing ? 'Analysis already running — showing live status' : `Analysis ${r.status}`);
    }
    catch (e) { toast('critical', e instanceof Error ? e.message : 'Analysis failed'); }
    finally { setStarting(false); }
  };
  const seekTo = (t: number, d?: Detection) => { player.current?.seek(t); if (d) setSel(d); };
  const detections = det.data ?? []; const motion = mot.data ?? [];
  const shown = detections.filter((d) => d.category === tab);
  const snapshots = (snaps.data ?? []).filter((s) => s.snapshot_url);
  return (
    <div className="grid xl:grid-cols-[minmax(0,1fr)_360px] gap-4">
      <div className="space-y-4 min-w-0">
        <ForensicVideoPlayer ref={player} evidenceId={evidence.id} selected={sel} initialTime={t0} onTime={setCur} onDuration={setDur} />
        <Panel title="FORENSIC TIMELINE"><VideoTimeline duration={dur} current={cur} detections={detections} motion={motion} onSeek={(t) => seekTo(t)} onPick={setSel} /></Panel>
        <Panel title="DETECTION SNAPSHOTS">
          {snapshots.length === 0 ? <p className="text-sm text-slate-500 font-mono tracking-wider">NO DATA AVAILABLE</p> : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {snapshots.map((s) => <button key={s.id} onClick={() => setPreview(s)} className="text-left border border-white/[0.07] rounded overflow-hidden hover:border-ice/50">
                <img src={mediaUrl(s.snapshot_url!)} alt={`${s.label} at ${fmtClock(s.timestamp)}`} loading="lazy" className="aspect-video w-full object-cover bg-black" />
                <div className="p-2 font-mono text-[11px]"><p className="text-slate-400">{s.frame != null ? `FRAME ${String(s.frame).padStart(5, '0')}` : fmtClock(s.timestamp)}</p><p className="text-ice">{s.label.toUpperCase()} {pct(s.confidence)}</p></div>
              </button>)}
            </div>
          )}
        </Panel>
      </div>
      <div className="space-y-4">
        {!ready && <Panel title="ANALYSIS OPTIONS">
          <label className="flex items-start gap-3 text-xs text-slate-300">
            <input type="checkbox" checked={tracking} onChange={(e) => setTracking(e.target.checked)} disabled={starting || state === 'processing' || state === 'pending'} className="mt-0.5" />
            <span><span className="block text-cool font-mono">BYTE TRACK · OPTIONAL</span><span className="block mt-1 text-slate-500">Real video-local track IDs. Track IDs are not person identities.</span></span>
          </label>
        </Panel>}
        {analysis.error ? <ErrorState error={analysis.error} onRetry={analysis.reload} /> : analysis.data ? <AnalysisStatus a={analysis.data} onStart={start} busy={starting} /> : <LoadingState compact label="LOADING ANALYSIS…" />}
        <Panel title="DETECTION INSPECTOR">
          <div className="flex gap-1 mb-3" role="tablist">{TABS.map((t) => {
            const n = t.id === 'motion' ? motion.length : detections.filter((d) => d.category === t.id).length;
            return <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)} className={`flex-1 text-[10px] font-mono tracking-wider py-1.5 border rounded-sm ${tab === t.id ? 'border-ice/50 text-ice bg-ice/10' : 'border-white/10 text-slate-400'}`}>{t.label} {n}</button>;
          })}</div>
          {!ready ? <p className="text-xs font-mono text-slate-500 tracking-wider">RUN ANALYSIS TO POPULATE DETECTIONS</p>
            : det.loading || mot.loading ? <LoadingState compact label="LOADING…" />
            : det.error ? <ErrorState error={det.error} onRetry={det.reload} />
            : tab === 'motion' ? (motion.length === 0 ? <EmptyState title="NO DATA AVAILABLE" /> :
              <ul className="max-h-80 overflow-auto space-y-1">{motion.map((m) => <li key={m.id}><button onClick={() => seekTo(m.start)} className="w-full text-left px-3 py-2 rounded hover:bg-white/5 font-mono text-xs"><span className="text-ice">{fmtClock(m.start)}</span></button></li>)}</ul>)
            : shown.length === 0 ? <EmptyState title="NO DATA AVAILABLE" /> :
              <ul className="max-h-80 overflow-auto space-y-1">{shown.map((d) => <li key={d.id}><button onClick={() => seekTo(d.timestamp, d)} className={`w-full flex justify-between px-3 py-2 rounded font-mono text-xs ${sel?.id === d.id ? 'bg-ice/10 text-ice' : 'hover:bg-white/5'}`}><span>{d.label.toUpperCase()} {d.track_id != null && <span className="text-ice">· TRACK {String(d.track_id).padStart(2, '0')}</span>} <span className="text-slate-500">{fmtClock(d.timestamp)}</span></span><span>{pct(d.confidence)}</span></button></li>)}</ul>}
        </Panel>
      </div>
      {preview && <div className="fixed inset-0 z-50 bg-black/85 flex items-center justify-center p-6" onClick={() => setPreview(null)} role="dialog" aria-modal="true" aria-label="Snapshot preview">
        <button className="absolute top-4 right-4 text-cool" aria-label="Close preview"><X /></button>
        <div className="max-w-5xl" onClick={(e) => e.stopPropagation()}><img src={mediaUrl(preview.snapshot_url!)} alt={preview.label} className="max-h-[80vh] rounded" />
          <p className="mt-2 font-mono text-xs text-ice">{preview.label.toUpperCase()} · {pct(preview.confidence)} · {fmtClock(preview.timestamp)}</p>
          <button className="btn-ghost mt-2" onClick={() => { seekTo(preview.timestamp, preview); setPreview(null); }}>SEEK VIDEO TO THIS FRAME</button>
        </div>
      </div>}
    </div>
  );
}
