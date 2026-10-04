import { useEffect, useState, type ReactNode } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Activity, ChevronLeft, ChevronRight, Clock, Command, Eye, FileText, Film, GitMerge, HelpCircle, LayoutGrid, LogOut, Menu, ScrollText, Search, Settings } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { getCase } from '../../api/cases';
import { pingBackend } from '../../api/client';
import { useAsync } from '../../hooks/useAsync';
import { Badge, Modal } from '../common/ui';

const NAV = [
  { to: 'overview', label: 'OVERVIEW', icon: LayoutGrid }, { to: 'evidence', label: 'EVIDENCE', icon: Film },
  { to: 'analysis', label: 'ANALYSIS', icon: Eye }, { to: 'timeline', label: 'TIMELINE', icon: Clock },
  { to: 'search', label: 'SEARCH', icon: Search }, { to: 'correlation', label: 'CORRELATION', icon: GitMerge },
  { to: 'custody', label: 'CHAIN OF CUSTODY', icon: ScrollText }, { to: 'reports', label: 'REPORTS', icon: FileText },
];

function useOnline() {
  const [on, setOn] = useState<boolean | null>(null);
  useEffect(() => {
    let live = true;
    const run = () => pingBackend().then((v) => live && setOn(v));
    run(); const t = setInterval(run, 30000);
    return () => { live = false; clearInterval(t); };
  }, []);
  return on;
}

function Palette({ open, onClose, caseId }: { open: boolean; onClose: () => void; caseId?: string }) {
  const nav = useNavigate();
  const [q, setQ] = useState(''); const [sel, setSel] = useState(0);
  const base = caseId ? `/cases/${caseId}` : '/cases';
  const cmds = caseId
    ? [['Open Evidence', `${base}/evidence`], ['Run Analysis', `${base}/analysis`], ['Search Events', `${base}/search`], ['Open Timeline', `${base}/timeline`], ['View Chain of Custody', `${base}/custody`], ['Generate Report', `${base}/reports`], ['Cross-Camera Correlation', `${base}/correlation`], ['All Cases', '/cases']]
    : [['All Cases', '/cases']];
  const items = cmds.filter(([l]) => l.toLowerCase().includes(q.toLowerCase()));
  useEffect(() => { setSel(0); }, [q]);
  useEffect(() => { if (open) setQ(''); }, [open]);
  const go = (to: string) => { nav(to); onClose(); };
  return (
    <Modal open={open} title="Command palette" onClose={onClose}>
      <input autoFocus className="input" placeholder="Type a command…" value={q} onChange={(e) => setQ(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown') { e.preventDefault(); setSel((s) => Math.min(s + 1, items.length - 1)); }
          if (e.key === 'ArrowUp') { e.preventDefault(); setSel((s) => Math.max(s - 1, 0)); }
          if (e.key === 'Enter' && items[sel]) go(items[sel][1]);
        }} />
      <ul className="mt-3 space-y-1">
        {items.map(([l, to], i) => (
          <li key={l}><button onClick={() => go(to)} className={`w-full text-left px-3 py-2 rounded text-sm ${i === sel ? 'bg-ice/10 text-ice' : 'hover:bg-white/5'}`}>{l}</button></li>
        ))}
        {items.length === 0 && <li className="text-sm text-slate-500 px-3 py-2">No matching command</li>}
      </ul>
    </Modal>
  );
}

export default function Shell({ caseId, children }: { caseId?: string; children: ReactNode }) {
  const { user, signOut } = useAuth();
  const loc = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [palette, setPalette] = useState(false);
  const online = useOnline();
  const c = useAsync(() => (caseId ? getCase(caseId) : Promise.resolve(null)), [caseId]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setPalette((v) => !v); } };
    window.addEventListener('keydown', h); return () => window.removeEventListener('keydown', h);
  }, []);
  useEffect(() => setMobile(false), [loc.pathname]);

  const cs = c.data;
  return (
    <div className="h-full flex flex-col">
      <header className="h-14 shrink-0 flex items-center gap-4 px-4 border-b border-white/[0.07] bg-bg1/90 backdrop-blur">
        <button className="md:hidden text-slate-300" aria-label="Open menu" onClick={() => setMobile((v) => !v)}><Menu size={18} /></button>
        <Link to="/cases" className="font-mono text-sm tracking-[0.2em] text-cool">ROCKET FORENSICS</Link>
        {cs && <span className="hidden sm:block font-mono text-xs text-ice">{cs.case_number}</span>}
        <div className="flex-1" />
        <button onClick={() => setPalette(true)} className="hidden sm:flex items-center gap-2 text-xs text-slate-400 border border-white/10 rounded px-2.5 py-1.5 hover:border-ice/50" aria-label="Open command palette">
          <Command size={12} /> Ctrl K
        </button>
        <span className="flex items-center gap-2 text-[10px] font-mono tracking-widest text-slate-400">
          <span className={`h-2 w-2 rounded-full ${online ? 'bg-ok animate-pulse' : online === false ? 'bg-crit' : 'bg-slate-600'}`} />
          {online ? 'SYSTEM ONLINE' : online === false ? 'BACKEND OFFLINE' : 'CHECKING'}
        </span>
        <div className="flex items-center gap-2.5 pl-3 border-l border-white/10">
          <div className="h-7 w-7 rounded-full bg-ice/15 border border-ice/40 flex items-center justify-center text-[11px] text-ice font-semibold" aria-hidden>{(user?.full_name ?? '?').slice(0, 1).toUpperCase()}</div>
          <span className="hidden md:block text-xs">{user?.full_name}</span>
          <button onClick={signOut} aria-label="Sign out" className="text-slate-400 hover:text-crit"><LogOut size={15} /></button>
        </div>
      </header>
      <div className="flex-1 min-h-0 flex relative">
        <aside className={`${mobile ? 'flex' : 'hidden'} md:flex absolute md:static z-30 h-full flex-col bg-bg1 border-r border-white/[0.07] transition-all ${collapsed ? 'md:w-16' : 'md:w-60'} w-60`}>
          <div className="p-3 flex-1 overflow-auto">
            {caseId && !collapsed && (
              <div className="mb-4 px-2">
                <p className="panel-title">CASE</p>
                <p className="mt-1 font-mono text-xs text-cool">{cs?.case_number ?? '…'}</p>
              </div>
            )}
            <nav className="space-y-0.5" aria-label="Case navigation">
              {!caseId && <NavLink to="/cases" className="flex items-center gap-3 px-2.5 py-2 rounded text-xs tracking-wider text-ice bg-ice/10"><Activity size={15} />{!collapsed && 'INVESTIGATION ARCHIVE'}</NavLink>}
              {caseId && NAV.map(({ to, label, icon: Icon }) => (
                <NavLink key={to} to={`/cases/${caseId}/${to}`} title={label}
                  className={({ isActive }) => `flex items-center gap-3 px-2.5 py-2 rounded text-xs tracking-wider ${isActive ? 'bg-ice/10 text-ice' : 'text-slate-400 hover:text-cool hover:bg-white/[0.04]'}`}>
                  <Icon size={15} />{!collapsed && label}
                </NavLink>
              ))}
              {caseId && <NavLink to="/cases" className="flex items-center gap-3 px-2.5 py-2 mt-3 rounded text-xs tracking-wider text-slate-500 hover:text-cool"><ChevronLeft size={15} />{!collapsed && 'ALL CASES'}</NavLink>}
            </nav>
          </div>
          <div className="p-3 border-t border-white/[0.06] space-y-0.5 text-slate-500 text-xs">
            <NavLink to="/settings" title="Settings" className="flex items-center gap-3 px-2.5 py-1.5 rounded text-slate-500 hover:text-cool hover:bg-white/[0.04]"><Settings size={14} />{!collapsed && 'Settings'}</NavLink>
            <NavLink to="/help" title="Help" className="flex items-center gap-3 px-2.5 py-1.5 rounded text-slate-500 hover:text-cool hover:bg-white/[0.04]"><HelpCircle size={14} />{!collapsed && 'Help'}</NavLink>
            <button onClick={() => setCollapsed((v) => !v)} className="hidden md:flex items-center gap-3 px-2.5 py-1.5 hover:text-cool w-full" aria-label="Toggle sidebar">
              {collapsed ? <ChevronRight size={14} /> : <><ChevronLeft size={14} />Collapse</>}
            </button>
          </div>
        </aside>
        <main className="flex-1 min-w-0 overflow-auto">
          {cs && (
            <div className="px-6 pt-5 pb-3 flex flex-wrap items-center gap-3">
              <div>
                <p className="font-mono text-xs text-ice">{cs.case_number}</p>
                <h1 className="text-lg font-semibold">{cs.title}</h1>
              </div>
              <Badge tone={cs.status === 'CLOSED' ? 'mute' : 'ice'}>{cs.status}</Badge>
            </div>
          )}
          <AnimatePresence mode="wait">
            <motion.div key={loc.pathname} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.18 }} className="px-6 pb-10 pt-2">
              {children}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
      <Palette open={palette} onClose={() => setPalette(false)} caseId={caseId} />
    </div>
  );
}
