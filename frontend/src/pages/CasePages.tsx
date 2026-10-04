import { useState, type FormEvent } from 'react';
import { Link, Outlet, useNavigate, useParams } from 'react-router-dom';
import { Check, Loader2, X } from 'lucide-react';
import { searchCase } from '../api/search';
import { caseCorrelation, caseTimeline } from '../api/timeline';
import { caseCustody } from '../api/custody';
import { generateReport } from '../api/reports';
import { listEvidence } from '../api/evidence';
import Shell from '../components/layout/AppShell';
import { Badge, Button, EmptyState, ErrorState, LoadingState, Panel } from '../components/common/ui';
import EvidenceCard from '../components/evidence/EvidenceCard';
import EvidenceUploader from '../components/evidence/EvidenceUploader';
import ForensicImageUploader from '../components/evidence/ForensicImageUploader';
import EvidenceWorkstation from '../components/video/EvidenceWorkstation';
import CustodyLedger from '../components/custody/CustodyLedger';
import ReportCard from '../components/reports/ReportCard';
import { useAsync } from '../hooks/useAsync';
import { useToast } from '../context/ToastContext';
import { evidenceLabel, fmtClock, pct } from '../lib/format';
import { acquireNetworkStream } from '../api/acquisition';
import type { TimelineEvent } from '../types';

const useCaseId = () => useParams().caseId as string;

export function CaseLayout() {
  const caseId = useCaseId();
  return <Shell caseId={caseId}><Outlet /></Shell>;
}

type Stage = 'completed' | 'processing' | 'pending' | 'failed';
const STAGE_STYLE: Record<Stage, string> = { completed: 'border-ok text-ok', processing: 'border-ice text-ice', pending: 'border-white/15 text-slate-500', failed: 'border-crit text-crit' };

export function Overview() {
  const caseId = useCaseId();
  const q = useAsync(async () => {
    const [ev, tl, co, cu] = await Promise.allSettled([listEvidence(caseId), caseTimeline(caseId), caseCorrelation(caseId), listEvidence(caseId).then(caseCustody)]);
    if (ev.status === 'rejected') throw ev.reason;
    const timeline = tl.status === 'fulfilled' ? tl.value : [];
    const correlation = co.status === 'fulfilled' ? co.value : { count: 0, disclaimer: 'NO DATA AVAILABLE', groups: [] };
    const custody = cu.status === 'fulfilled' ? cu.value : [];
    return { ev: ev.value, tl: timeline, co: correlation, cu: custody };
  }, [caseId]);
  if (q.loading && !q.data) return <LoadingState label="LOADING CASE…" />;
  if (q.error || !q.data) return <ErrorState error={q.error} onRetry={q.reload} />;
  const { ev, tl, co, cu } = q.data;
  const cams = new Set(ev.map((e) => e.camera_id).filter(Boolean)).size;
  const verified = ev.filter((e) => e.integrity === 'verified').length;
  const failed = ev.some((e) => e.integrity === 'failed');
  const an = ev.map((e) => e.analysis_status?.toLowerCase());
  const anDone = an.filter((s) => s === 'completed').length;
  const anRun = an.some((s) => s === 'processing' || s === 'running');
  const anFail = an.some((s) => s === 'failed');
  const stages: [string, Stage][] = [
    ['ACQUIRE', ev.length ? 'completed' : 'pending'],
    ['VERIFY', failed ? 'failed' : ev.length && verified === ev.length ? 'completed' : 'pending'],
    ['IDENTIFY', ev.some((e) => e.device?.known) ? 'completed' : 'pending'],
    ['ANALYZE', anFail ? 'failed' : anRun ? 'processing' : ev.length && anDone === ev.length ? 'completed' : 'pending'],
    ['CORRELATE', co.groups.length ? 'completed' : 'pending'],
    ['PRESERVE', cu.length ? 'completed' : 'pending'],
    ['REPORT', 'pending'],
  ];
  const stats: [string, string][] = [
    ['EVIDENCE', String(ev.length)], ['CAMERAS', cams ? String(cams) : 'NO DATA'], ['ANALYSIS', ev.length ? `${anDone}/${ev.length} DONE` : 'NO DATA'],
    ['TIMELINE EVENTS', String(tl.length)], ['INTEGRITY', failed ? 'FAILURE' : ev.length ? `${verified}/${ev.length} VERIFIED` : 'NO DATA'],
  ];
  return (
    <div className="space-y-6">
      <Panel title="EVIDENCE LIFECYCLE">
        <ol className="grid grid-cols-2 md:grid-cols-7 gap-3">
          {stages.map(([n, s], i) => (
            <li key={n} className={`border rounded p-3 ${STAGE_STYLE[s]}`}>
              <div className="flex items-center justify-between font-mono text-[10px] text-slate-500"><span>{i + 1}</span>
                {s === 'completed' ? <Check size={12} /> : s === 'failed' ? <X size={12} /> : s === 'processing' ? <Loader2 size={12} className="animate-spin" /> : null}</div>
              <p className="mt-2 font-mono text-xs tracking-[0.12em]">{n}</p>
              <p className="mt-1 text-[10px] font-mono uppercase opacity-80">{s}</p>
            </li>
          ))}
        </ol>
      </Panel>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {stats.map(([k, v]) => <div key={k} className={`panel p-4 ${k === 'INTEGRITY' && failed ? 'border-crit/50' : ''}`}><p className="panel-title">{k}</p><p className="mt-2 font-mono text-lg">{v}</p></div>)}
      </div>
    </div>
  );
}

export function Vault() {
  const caseId = useCaseId();
  const q = useAsync(() => listEvidence(caseId), [caseId]);
  const [open, setOpen] = useState(false);
  const [networkUrl, setNetworkUrl] = useState('');
  const [cameraId, setCameraId] = useState('');
  const [duration, setDuration] = useState('30');
  const [networkBusy, setNetworkBusy] = useState(false);
  const [networkMsg, setNetworkMsg] = useState('');
  const toast = useToast();
  const captureNetwork = async () => {
    if (!networkUrl.trim()) return;
    setNetworkBusy(true); setNetworkMsg('ACQUIRING STANDARD STREAM…');
    try {
      await acquireNetworkStream({ case_id: caseId, source_url: networkUrl.trim(), camera_id: cameraId.trim() || undefined, duration_seconds: Math.min(300, Math.max(1, Number(duration) || 30)) });
      setNetworkMsg('STREAM ACQUIRED • HASHED • READY'); setNetworkUrl('');
      q.reload(); toast('success', 'Network stream acquired as evidence');
    } catch (e) { setNetworkMsg('ACQUISITION FAILED'); toast('critical', e instanceof Error ? e.message : 'Network acquisition failed'); }
    finally { setNetworkBusy(false); }
  };
  return (
    <div>
      <div className="flex items-end justify-between mb-5"><h2 className="panel-title text-sm">EVIDENCE VAULT</h2><div className="flex gap-2"><Button onClick={() => setOpen((v) => !v)}>{open ? 'CLOSE' : 'ACQUIRE EVIDENCE'}</Button></div></div>
      {open && <Panel title="ACQUIRE EVIDENCE" className="mb-6"><div className="space-y-6"><EvidenceUploader caseId={caseId} onDone={q.reload} />
        <div className="border-t border-white/10 pt-5"><p className="panel-title mb-3">STANDARD NETWORK ACQUISITION</p><p className="text-xs text-slate-500 mb-3">Capture a recorder/camera stream exposed through RTSP, HTTP(S), or RTMP. This is standard stream acquisition, not proprietary DVR filesystem acquisition.</p><div className="grid md:grid-cols-[1fr_160px_120px_auto] gap-2"><input className="input" placeholder="rtsp://recorder/camera…" value={networkUrl} onChange={e => setNetworkUrl(e.target.value)} /><input className="input" placeholder="Camera ID" value={cameraId} onChange={e => setCameraId(e.target.value)} /><input className="input" type="number" min="1" max="300" value={duration} onChange={e => setDuration(e.target.value)} /><Button busy={networkBusy} onClick={captureNetwork}>CAPTURE</Button></div>{networkMsg && <p className="mt-2 font-mono text-[10px] text-ice">{networkMsg}</p>}</div>
        <div className="border-t border-white/10 pt-5"><p className="panel-title mb-3">FORENSIC IMAGE INGESTION</p><ForensicImageUploader caseId={caseId} /></div></div></Panel>}
      {q.loading && !q.data ? <LoadingState label="OPENING VAULT…" />
        : q.error ? <ErrorState error={q.error} onRetry={q.reload} />
        : !q.data || q.data.length === 0 ? <EmptyState title="NO EVIDENCE ACQUIRED" text="Upload your first surveillance recording to begin forensic analysis." action={<Button onClick={() => setOpen(true)}>ACQUIRE EVIDENCE</Button>} />
        : <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">{q.data.map((e) => <EvidenceCard key={e.id} e={e} onChanged={q.reload} />)}</div>}
    </div>
  );
}

export function AnalysisPage() {
  const caseId = useCaseId();
  const q = useAsync(() => listEvidence(caseId), [caseId]);
  const [pick, setPick] = useState<string>('');
  if (q.loading && !q.data) return <LoadingState label="LOADING EVIDENCE…" />;
  if (q.error) return <ErrorState error={q.error} onRetry={q.reload} />;
  if (!q.data?.length) return <EmptyState title="NO EVIDENCE ACQUIRED" text="Acquire a recording before running analysis." action={<Link to={`/cases/${caseId}/evidence`} className="btn-primary">ACQUIRE EVIDENCE</Link>} />;
  const ev = q.data.find((e) => e.id === pick) ?? q.data[0];
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3"><h2 className="panel-title text-sm">VIDEO ANALYSIS WORKSTATION</h2>
        <select aria-label="Select evidence" className="input max-w-xs" value={ev.id} onChange={(e) => setPick(e.target.value)}>{q.data.map((e) => <option key={e.id} value={e.id}>{evidenceLabel(e.id)} · {e.filename}</option>)}</select>
      </div>
      <EvidenceWorkstation key={ev.id} evidence={ev} />
    </div>
  );
}

function EventLink({ e }: { e: TimelineEvent }) {
  const nav = useNavigate();
  return (
    <button disabled={!e.evidence_id} onClick={() => e.evidence_id && nav(`/evidence/${e.evidence_id}?t=${Math.floor(e.timestamp)}`)}
      className="w-full text-left flex items-center gap-4 px-3 py-2.5 rounded hover:bg-white/[0.04] disabled:hover:bg-transparent border-b border-white/[0.04]">
      <span className="mono text-sm text-ice w-20">{e.wallClock ? e.wallClock.slice(11, 19) || e.wallClock : fmtClock(e.timestamp)}</span>
      <Badge tone="ice">{e.type}</Badge>
      <span className="text-sm flex-1 truncate">{e.label}</span>
      {e.camera && <span className="mono text-xs text-slate-400">{e.camera}</span>}
      {e.confidence != null && <span className="mono text-xs text-slate-500">{pct(e.confidence)}</span>}
    </button>
  );
}

export function TimelinePage() {
  const caseId = useCaseId();
  const q = useAsync(() => caseTimeline(caseId), [caseId]);
  const [type, setType] = useState('all');
  if (q.loading && !q.data) return <LoadingState label="LOADING TIMELINE…" />;
  if (q.error) return <ErrorState error={q.error} onRetry={q.reload} />;
  const all = q.data ?? [];
  const types = ['all', ...Array.from(new Set(all.map((e) => e.type)))];
  const items = all.filter((e) => type === 'all' || e.type === type).sort((a, b) => a.timestamp - b.timestamp);
  return (
    <Panel title="FORENSIC TIMELINE" right={<div className="flex gap-1">{types.map((t) => <button key={t} onClick={() => setType(t)} className={`text-[10px] font-mono px-2 py-1 border rounded-sm uppercase ${type === t ? 'border-ice/50 text-ice' : 'border-white/10 text-slate-400'}`}>{t}</button>)}</div>}>
      {items.length === 0 ? <EmptyState title="NO DATA AVAILABLE" text="Timeline events appear after analysis completes." /> : items.map((e) => <EventLink key={e.id} e={e} />)}
    </Panel>
  );
}

export function SearchPage() {
  const caseId = useCaseId();
  const [f, setF] = useState({ object: '', camera: '', from: '', to: '', min_confidence: '', evidence_id: '', limit: '500' });
  const [res, setRes] = useState<TimelineEvent[] | null>(null);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState<unknown>(null);
  const submit = async (e: FormEvent) => { e.preventDefault(); setBusy(true); setErr(null); try { setRes(await searchCase(caseId, f)); } catch (x) { setErr(x); } finally { setBusy(false); } };
  const fld = (k: keyof typeof f, label: string, ph = '', type = 'text') => (
    <label className="block"><span className="text-xs text-slate-400">{label}</span><input type={type} className="input mt-1" placeholder={ph} value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></label>
  );
  return (
    <div className="space-y-4">
      <Panel title="EVIDENCE SEARCH">
        <form onSubmit={submit} className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3 items-end">
          {fld('object', 'Object', 'person')}{fld('camera', 'Camera', 'CAM-01')}{fld('from', 'From', '', 'datetime-local')}{fld('to', 'To', '', 'datetime-local')}{fld('min_confidence', 'Min confidence', '0.35')}
          <Button type="submit" busy={busy}>SEARCH</Button>
        </form>
      </Panel>
      {err !== null && <ErrorState error={err} />}
      {res && <Panel title={`RESULTS · ${res.length}`}>{res.length === 0 ? <EmptyState title="NO MATCHING EVENTS" /> : res.map((e) => <EventLink key={e.id} e={e} />)}</Panel>}
    </div>
  );
}

export function CorrelationPage() {
  const caseId = useCaseId(); const nav = useNavigate();
  const q = useAsync(() => caseCorrelation(caseId), [caseId]);
  if (q.loading && !q.data) return <LoadingState label="CORRELATING EVENTS…" />;
  if (q.error) return <ErrorState error={q.error} onRetry={q.reload} />;
  if (!q.data?.groups.length) return <EmptyState title="NO DATA AVAILABLE" text="No temporally correlated events were returned for this case." />;
  return <div className="space-y-3"><p className="text-xs font-mono text-slate-500">{q.data.disclaimer}</p><div className="grid lg:grid-cols-2 gap-4">{q.data.groups.map((g) => (
    <div key={g.group_id} className="panel p-4">
      <p className="panel-title">TEMPORALLY CORRELATED · {g.class_name.toUpperCase()}</p>
      <p className="mono text-xs text-slate-500 mt-1">{g.event_count} events · {g.window_seconds}s window · {g.cameras.join(' · ')}</p>
      <div className="mt-3 space-y-2">{g.events.map((e) => (
        <button key={e.event_id} disabled={!e.evidence_id} onClick={() => e.evidence_id && nav(`/evidence/${e.evidence_id}?t=${Math.floor(e.video_time_seconds ?? 0)}`)}
          className="w-full text-left panel p-3 hover:border-ice/40 disabled:opacity-60">
          <p className="mono text-xs text-ice">{e.camera_id ?? 'CAMERA —'}</p>
          <p className="mono text-sm mt-1">{e.timestamp ?? 'NO DATA AVAILABLE'}</p>
          <p className="text-xs text-slate-400 mt-1">Evidence {e.evidence_id ?? 'NO DATA AVAILABLE'}</p>
        </button>
      ))}</div>
    </div>
  ))}</div></div>;
}

export function CustodyPage() {
  const caseId = useCaseId();
  const q = useAsync(async () => { const ev = await listEvidence(caseId); return caseCustody(ev); }, [caseId]);
  if (q.loading && !q.data) return <LoadingState label="READING LEDGER…" />;
  if (q.error) return <ErrorState error={q.error} onRetry={q.reload} />;
  return <Panel title="CHAIN OF CUSTODY">{q.data?.length ? <CustodyLedger events={q.data} /> : <EmptyState title="NO DATA AVAILABLE" />}</Panel>;
}

export function ReportsPage() {
  const caseId = useCaseId(); const toast = useToast();
  const [reports, setReports] = useState<import('../types').ForensicReport[]>([]);
  const [busy, setBusy] = useState(false);
  const gen = async () => {
    setBusy(true);
    try {
      const evidence = await listEvidence(caseId);
      const report = await generateReport(caseId, evidence.map((e) => e.id));
      setReports((prev) => [report, ...prev.filter((r) => r.id !== report.id)]);
      toast('success', 'Report generated');
    } catch (e) { toast('critical', e instanceof Error ? e.message : 'Report failed'); }
    finally { setBusy(false); }
  };
  return (
    <div>
      <div className="flex items-center justify-between mb-5"><h2 className="panel-title text-sm">FORENSIC REPORTS</h2><Button busy={busy} onClick={gen}>GENERATE REPORT</Button></div>
      {busy && <LoadingState compact label="GENERATING REPORT…" />}
      {!reports.length && !busy ? <EmptyState title="NO DATA AVAILABLE" text="Generate a report to produce a downloadable PDF of this investigation." />
        : <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">{reports.map((r) => <ReportCard key={r.id} r={r} />)}</div>}
    </div>
  );
}
