import { useState, type FormEvent, type ReactNode } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { register } from '../api/auth';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { Button, ErrorState } from '../components/common/ui';

function Frame({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="min-h-full flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <Link to="/" className="block font-mono text-sm tracking-[0.22em] mb-1">ROCKET FORENSICS</Link>
        <p className="text-xs text-slate-500 mb-6">Acquire. Validate. Analyze. Correlate. Report.</p>
        <div className="panel p-6"><h1 className="panel-title mb-5">{title}</h1>{children}</div>
      </div>
    </div>
  );
}
const F = ({ label, ...p }: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) => (
  <label className="block mb-4"><span className="text-xs text-slate-400">{label}</span><input {...p} className="input mt-1" required /></label>
);

export function Login() {
  const { user, signIn } = useAuth(); const nav = useNavigate();
  const [email, setEmail] = useState(''); const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false); const [err, setErr] = useState<unknown>(null);
  if (user) return <Navigate to="/cases" replace />;
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try { await signIn(email, password); nav('/cases'); } catch (x) { setErr(x); } finally { setBusy(false); }
  };
  return (
    <Frame title="SIGN IN">
      <form onSubmit={submit}>
        <F label="Email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <F label="Password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
        {err !== null && <div className="mb-4"><ErrorState error={err} title="SIGN IN FAILED" /></div>}
        <Button type="submit" busy={busy} className="w-full">SIGN IN</Button>
      </form>
      <p className="mt-4 text-xs text-slate-500">No account? <Link className="text-ice" to="/register">Create one</Link></p>
    </Frame>
  );
}

export function Register() {
  const nav = useNavigate(); const toast = useToast(); const { signIn } = useAuth();
  const [f, setF] = useState({ full_name: '', email: '', organization: '', password: '', confirm: '' });
  const [busy, setBusy] = useState(false); const [err, setErr] = useState<unknown>(null);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (f.password !== f.confirm) { setErr(new Error('Passwords do not match')); return; }
    setBusy(true); setErr(null);
    try { await register({ full_name: f.full_name, email: f.email, organization: f.organization, password: f.password }); toast('success', 'Account created.');
      try { await signIn(f.email, f.password); nav('/cases'); }
      catch { toast('info', 'Account created. Please sign in.'); nav('/login'); } }
    catch (x) { setErr(x); } finally { setBusy(false); }
  };
  return (
    <Frame title="CREATE ACCOUNT">
      <form onSubmit={submit}>
        <F label="Full name" value={f.full_name} onChange={set('full_name')} autoComplete="name" />
        <F label="Email" type="email" value={f.email} onChange={set('email')} autoComplete="email" />
        <F label="Organization" value={f.organization} onChange={set('organization')} />
        <F label="Password" type="password" minLength={8} value={f.password} onChange={set('password')} autoComplete="new-password" />
        <F label="Confirm password" type="password" value={f.confirm} onChange={set('confirm')} autoComplete="new-password" />
        {err !== null && <div className="mb-4"><ErrorState error={err} title="REGISTRATION FAILED" /></div>}
        <Button type="submit" busy={busy} className="w-full">CREATE ACCOUNT</Button>
      </form>
      <p className="mt-4 text-xs text-slate-500">Already registered? <Link className="text-ice" to="/login">Sign in</Link></p>
    </Frame>
  );
}
