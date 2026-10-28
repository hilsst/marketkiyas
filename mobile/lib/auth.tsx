import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { api, setApiToken, setUnauthorizedHandler, User } from '@/lib/api';
import { loadToken, saveToken } from '@/lib/session';

interface AuthState {
  user: User | null;
  ready: boolean; // kayıtlı oturum okundu mu (okunana kadar giriş ekranı gösterilmez)
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  const signOut = useCallback(async () => {
    setApiToken(null);
    setUser(null);
    await saveToken(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => { void signOut(); });
    (async () => {
      const saved = await loadToken();
      if (saved) {
        setApiToken(saved);
        try { setUser(await api.me()); } catch { await signOut(); }
      }
      setReady(true);
    })();
    return () => setUnauthorizedHandler(null);
  }, [signOut]);

  const start = useCallback(async (token: string, next: User) => {
    setApiToken(token);
    await saveToken(token);
    setUser(next);
  }, []);

  const value = useMemo<AuthState>(() => ({
    user,
    ready,
    login: async (email, password) => { const r = await api.login(email.trim(), password); await start(r.access_token, r.user); },
    register: async (email, password, fullName) => {
      const r = await api.register(email.trim(), password, fullName?.trim());
      await start(r.access_token, r.user);
    },
    logout: signOut,
  }), [user, ready, start, signOut]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth, AuthProvider içinde kullanılmalı');
  return ctx;
}
