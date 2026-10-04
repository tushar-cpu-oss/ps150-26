import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { createCase, listCases } from '../api/cases';
import Shell from '../components/layout/AppShell';
import { Badge, Button, EmptyState, ErrorState, LoadingState, Modal } from '../components/common/ui';
import { useAsync } from '../hooks/useAsync';
import { useToast } from '../context/ToastContext';
import { fmtDate } from '../lib/format';

export default function Cases() {
  const q = useAsync(listCases, []); const nav = useNavigate(); const toast = useToast();
  const [open, setOpen] = useState(false); const [busy, setBusy] = useState(false); const [err, setErr] = useState<unknown>(null);
  const [f, setF] = useState({ case_number: '', title: '', description: '' });
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try { const c = await createCase(f); toast('success', 'Case created'); setOpen(false); nav(`/cases/${c.id}/overview`); }
    catch (x) { setErr(x); } finally { setBusy(false); }
  };
  return (
    <Shell>
      <div className="flex items-end justify-between mb-6 mt-3">
        <div><p className="panel-title">INVESTIGATION ARCHIVE</p><h1 className="text-xl font-semibold mt-1">Cases</h1></div>
        <Button onClick={() => setOpen(true)}>CREATE CASE</Button>
      </div>
      {q.loading && !q.data ? <LoadingState label="LOADING ARCHIVE…" />
        : q.error ? <ErrorState error={q.error} onRetry={q.reload} />
        : q.data && q.data.length === 0 ? <EmptyState title="NO CASES YET" text="Create a case to start acquiring evidence." action={<Button onClick={() => setOpen(true)}>CREATE CASE</Button>} />
        : (
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
            {q.data?.map((c) => (
              <article key={c.id} className="panel p-5 hover:border-ice/30 transition-colors">
                <div className="flex justify-between items-start"><p className="font-mono text-xs text-ice">{c.case_number}</p><Badge tone="ice">{c.status}</Badge></div>
                <h2 className="mt-2 font-medium">{c.title}</h2>
                <dl className="mt-4 grid grid-cols-2 gap-2 font-mono text-[11px] text-slate-400">
                  <div><dt className="panel-title">EVIDENCE</dt><dd className="text-cool text-sm">{c.evidence_count ?? '—'}</dd></div>
                  <div><dt className="panel-title">EVENTS</dt><dd className="text-cool text-sm">{c.event_count ?? '—'}</dd></div>
                  <div className="col-span-2"><dt className="panel-title">LAST ACTIVITY</dt><dd>{fmtDate(c.updated_at ?? c.created_at)}</dd></div>
                </dl>
                <Link to={`/cases/${c.id}/overview`} className="btn-primary mt-5 w-full">OPEN CASE</Link>
              </article>
            ))}
          </div>
        )}
      <Modal open={open} title="Create case" onClose={() => setOpen(false)}>
        <form onSubmit={submit} className="space-y-4">
          <label className="block"><span className="text-xs text-slate-400">Case number</span><input className="input mt-1" required placeholder="CASE-2026-001" value={f.case_number} onChange={(e) => setF({ ...f, case_number: e.target.value })} /></label>
          <label className="block"><span className="text-xs text-slate-400">Title</span><input className="input mt-1" required value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></label>
          <label className="block"><span className="text-xs text-slate-400">Description</span><textarea className="input mt-1" rows={3} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></label>
          {err !== null && <ErrorState error={err} title="COULD NOT CREATE CASE" />}
          <Button type="submit" busy={busy}>CREATE CASE</Button>
        </form>
      </Modal>
    </Shell>
  );
}
