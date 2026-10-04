import { lazy, Suspense, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, Film, Fingerprint, GitMerge, ScrollText, ShieldCheck } from 'lucide-react';
import { LoadingState } from '../components/common/ui';
import { Network2D } from '../components/3d/EvidenceNetwork';

const Network = lazy(() => import('../components/3d/EvidenceNetwork'));
const CAPS = [
  { icon: Film, t: 'EVIDENCE ACQUISITION', d: 'Ingest DVR/NVR exports with hashes computed on arrival.' },
  { icon: ShieldCheck, t: 'INTEGRITY VERIFICATION', d: 'Re-verify SHA-256 and MD5 at any point in the investigation.' },
  { icon: Fingerprint, t: 'DEVICE IDENTIFICATION', d: 'Fingerprint the recording device from container evidence.' },
  { icon: Eye, t: 'AI VIDEO ANALYSIS', d: 'YOLO detections and motion events with frame-level timestamps.' },
  { icon: GitMerge, t: 'EVENT CORRELATION', d: 'Temporal correlation of events across cameras.' },
  { icon: ScrollText, t: 'FORENSIC REPORTING', d: 'Custody ledger and PDF reports generated from case data.' },
];
const PIPE = ['ACQUIRE', 'VERIFY', 'IDENTIFY', 'ANALYZE', 'CORRELATE', 'PRESERVE', 'REPORT'];

export default function Landing() {
  const nav = useNavigate();
  const [active, setActive] = useState<number | null>(null);
  const go = () => nav('/cases');
  return (
    <div className="min-h-full">
      <header className="flex items-center justify-between px-6 lg:px-12 h-16">
        <p className="font-mono text-sm tracking-[0.22em]">TEAM ROCKET</p>
        <nav className="flex gap-3"><Link to="/login" className="btn-ghost">SIGN IN</Link><Link to="/register" className="btn-primary">CREATE ACCOUNT</Link></nav>
      </header>
      <section className="px-6 lg:px-12 grid lg:grid-cols-2 gap-6 items-center min-h-[80vh]">
        <div>
          <p className="font-mono text-xs tracking-[0.2em] text-ice-dim">ROCKET FORENSICS · DIGITAL EVIDENCE INTELLIGENCE</p>
          <h1 className="mt-5 text-5xl md:text-7xl font-semibold leading-[1.02] tracking-tight">
            Acquire.<br />Validate.<br />Analyze.<br />Correlate.<br />Report.
          </h1>
          <p className="mt-6 max-w-md text-slate-400 leading-relaxed">A unified forensic workspace for acquiring, verifying and analyzing surveillance evidence across multiple DVR/NVR environments.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <button className="btn-primary" onClick={go}>ENTER FORENSIC WORKSPACE</button>
            <a href="#platform" className="btn-ghost">VIEW PLATFORM</a>
          </div>
        </div>
        <div className="h-[420px] lg:h-[560px] panel bg-bg1/40">
          <Suspense fallback={<Network2D onSelect={go} />}><Network onSelect={go} /></Suspense>
        </div>
      </section>
      <section id="platform" className="px-6 lg:px-12 py-20">
        <p className="panel-title">PLATFORM CAPABILITIES</p>
        <div className="mt-6 grid md:grid-cols-2 lg:grid-cols-3 gap-px bg-white/[0.07] border border-white/[0.07]">
          {CAPS.map((c, i) => (
            <div key={c.t} onMouseEnter={() => setActive(i)} onMouseLeave={() => setActive(null)} onFocus={() => setActive(i)} onBlur={() => setActive(null)} tabIndex={0}
              className={`bg-bg1 p-6 transition-colors ${active === i ? 'bg-panel2' : ''}`}>
              <c.icon size={20} className={active === i ? 'text-ice' : 'text-slate-500'} />
              <h3 className="mt-4 font-mono text-xs tracking-[0.14em]">{c.t}</h3>
              <p className="mt-2 text-sm text-slate-400">{c.d}</p>
            </div>
          ))}
        </div>
      </section>
      <section className="px-6 lg:px-12 pb-24">
        <p className="panel-title">FORENSIC PIPELINE</p>
        <ol className="mt-6 flex flex-col md:flex-row gap-2 md:gap-0">
          {PIPE.map((s, i) => (
            <li key={s} className="flex-1 flex md:flex-col items-center md:items-start gap-3 md:gap-2">
              <div className="flex md:w-full items-center"><span className="h-3 w-3 rounded-full border border-ice bg-bg0" /><span className="hidden md:block flex-1 h-px bg-ice/30" /></div>
              <span className="font-mono text-xs tracking-[0.16em]">{s}</span>
              <span className="sr-only">step {i + 1}</span>
            </li>
          ))}
        </ol>
      </section>
      <footer className="border-t border-white/[0.07] px-6 lg:px-12 py-8 flex flex-wrap justify-between gap-2 font-mono text-[11px] tracking-[0.18em] text-slate-500">
        <span>TEAM ROCKET</span><span>ROCKET FORENSICS</span><span>SIH PROTOTYPE</span>
      </footer>
    </div>
  );
}
