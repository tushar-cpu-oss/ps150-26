import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, BookOpen } from 'lucide-react';
import Shell from '../components/layout/AppShell';
import { Panel } from '../components/common/ui';

const KEY = 'rocket-ui-settings';
type Settings = { animation: 'full' | 'reduced'; };
const DEFAULTS: Settings = { animation: 'full' };

function load(): Settings { try { return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY) || '{}') }; } catch { return DEFAULTS; } }
function save(v: Settings) { localStorage.setItem(KEY, JSON.stringify(v)); window.dispatchEvent(new Event('rocket-settings')); }

export function SettingsPage() {
  const [s, setS] = useState<Settings>(load);
  useEffect(() => { document.documentElement.dataset.rocketMotion = s.animation; }, [s.animation]);
  const update = (patch: Partial<Settings>) => { const next = { ...s, ...patch }; setS(next); save(next); };
  return <Shell>
    <div className="max-w-3xl space-y-5">
      <div><p className="panel-title">SYSTEM PREFERENCES</p><h1 className="text-2xl font-semibold mt-1">Settings</h1><p className="text-sm text-slate-500 mt-1">Local workstation preferences. Forensic evidence and analysis settings are controlled by the case workflow.</p></div>
      <Panel title="INTERFACE">
        <div className="grid md:grid-cols-2 gap-4">
          <label className="panel p-4"><span className="panel-title">WORKSTATION MOTION</span><p className="text-xs text-slate-500 mt-2">Controls UI transition intensity. Evidence analysis is unaffected.</p><select className="input mt-2" value={s.animation} onChange={e => update({ animation: e.target.value as Settings['animation'] })}><option value="full">Full</option><option value="reduced">Reduced</option></select></label>
          <div className="panel p-4"><span className="panel-title">EVIDENCE MODE</span><p className="text-xs text-slate-500 mt-2">Original evidence remains read-only regardless of interface preferences.</p><p className="mt-3 font-mono text-xs text-ok">PRESERVATION LOCK · ACTIVE</p></div>
        </div>
      </Panel>
      <Panel title="FORENSIC SAFETY">
        <div className="grid md:grid-cols-3 gap-3 text-xs font-mono">
          <div className="border border-white/10 rounded p-3"><p className="text-ok">ORIGINALS</p><p className="mt-1 text-slate-500">Read-only during analysis.</p></div>
          <div className="border border-white/10 rounded p-3"><p className="text-ok">HASHING</p><p className="mt-1 text-slate-500">MD5 + SHA-256 are computed from stored bytes.</p></div>
          <div className="border border-white/10 rounded p-3"><p className="text-ok">IDENTITY</p><p className="mt-1 text-slate-500">Track IDs never imply person identity.</p></div>
        </div>
      </Panel>
      <Link to="/cases" className="inline-flex items-center gap-2 text-xs text-ice"><ArrowLeft size={14}/> BACK TO CASES</Link>
    </div>
  </Shell>;
}

export function HelpPage() {
  const sections = [
    ['Acquire evidence', 'Upload the original recording or ingest a supported forensic image. The original evidence is preserved and hashed before analysis.'],
    ['Verify integrity', 'Use the integrity panel to recompute MD5 and SHA-256 and compare them with acquisition values.'],
    ['Analyze', 'Run object, face and motion analysis. Optional ByteTrack creates video-local track IDs; it does not identify people.'],
    ['Correlate', 'Cross-camera correlation is temporal only. It does not establish that two detections are the same individual.'],
    ['Preserve and report', 'Chain-of-custody records actor-stamped actions and the report captures hashes, metadata, analysis and limitations.'],
  ];
  return <Shell>
    <div className="max-w-4xl space-y-5">
      <div><p className="panel-title">OPERATIONS GUIDE</p><h1 className="text-2xl font-semibold mt-1">Help & Methodology</h1><p className="text-sm text-slate-500 mt-1">How the prototype handles evidence and where its forensic boundaries are.</p></div>
      <div className="grid md:grid-cols-2 gap-4">{sections.map(([title, text]) => <Panel key={title} title={title.toUpperCase()}><p className="text-sm leading-6 text-slate-400">{text}</p></Panel>)}</div>
      <Panel title="IMPORTANT LIMITATIONS"><ul className="text-sm text-slate-400 space-y-2 list-disc pl-5"><li>OEM-proprietary DVR/NVR filesystem parsing requires validated vendor samples/protocols.</li><li>Standard RTSP/RTSPS/HTTP(S)/RTMP stream acquisition is supported when a recorder/camera exposes a compatible stream; private OEM DVR protocols remain separate.</li><li>Forensic-image baseline inspection now fingerprints common OEM markers and enumerates candidate media/recorder artifacts; this does not claim proprietary filesystem reconstruction.</li><li>Standard carving/recovery and FFmpeg-supported CCTV decoding are distinct from OEM database reconstruction.</li><li>AI detections require human forensic validation and are not legal conclusions.</li></ul></Panel>
      <div className="flex gap-3"><Link to="/cases" className="btn-primary"><ArrowLeft size={14}/> CASES</Link><Link to="/" className="btn-ghost"><BookOpen size={14}/> PRODUCT OVERVIEW</Link></div>
    </div>
  </Shell>;
}
