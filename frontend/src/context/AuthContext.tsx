import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import * as authApi from '../api/auth';
import { setUnauthorizedHandler, tokenStore } from '../api/client';
import type { User } from '../types';

interface AuthCtx {
  user: User | null; loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}
const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const signOut = useCallback(() => { tokenStore.clear(); setUser(null); setLoading(false); }, []);
  useEffect(() => {
    setUnauthorizedHandler(() => { tokenStore.clear(); setUser(null); setLoading(false); });
    return () => setUnauthorizedHandler(null);
  }, []);
  useEffect(() => {
    const token = tokenStore.get();
    if (!token) { setLoading(false); return; }
    authApi.me().then(setUser).catch(() => { tokenStore.clear(); setUser(null); }).finally(() => setLoading(false));
  }, []);
  const signIn = useCallback(async (email: string, password: string) => {
    setLoading(true);
    try {
      const token = await authApi.login(email, password);
      tokenStore.set(token);
      setUser(await authApi.me());
    } finally { setLoading(false); }
  }, []);
  const value = useMemo(() => ({ user, loading, signIn, signOut }), [user, loading, signIn, signOut]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
export function useAuth(): AuthCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('useAuth outside AuthProvider');
  return c;
}
