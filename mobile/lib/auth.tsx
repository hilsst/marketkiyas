import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { api, ApiError, AuthResponse, setApiToken, setUnauthorizedHandler, User } from '@/lib/api';
import { loadToken, saveToken } from '@/lib/session';

interface AuthState {
  user: User | null;
  ready: boolean; // kayıtlı oturum okundu mu (okunana kadar giriş ekranı gösterilmez)
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  upgrade: (email: string, password: string, fullName?: string) => Promise<void>; // misafiri gerçek hesaba çevirir, veriler kalır
  logout: () => Promise<void>;
  startSession: (r: AuthResponse) => Promise<void>; // şifre sıfırlama ve Google girişi oturumu buradan açar
  deleteAccount: (password?: string) => Promise<void>;
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

  // Hesapsız başlangıç: oturum yoksa sessizce misafir açılır; sunucuya ulaşılamazsa kullanıcı boş kalır (eskisi gibi)
  const startGuest = useCallback(async () => {
    try {
      const r = await api.guest();
      setApiToken(r.access_token);
      await saveToken(r.access_token);
      setUser(r.user);
    } catch { /* çevrimdışı: giriş ekranı eskisi gibi çalışır */ }
  }, []);

  useEffect(() => {
    let booting = true; // açılışta 401'i aşağıdaki catch ele alır; çift misafir açılmasın
    // Paralel isteklerin hepsi aynı anda 401 alır: tek bir kurtarma (yeni misafir) çalışsın
    let recovering: Promise<void> | null = null;
    setUnauthorizedHandler(() => {
      if (booting || recovering) return;
      recovering = signOut().then(startGuest).finally(() => { recovering = null; });
    });
    (async () => {
      const saved = await loadToken();
      if (saved) {
        setApiToken(saved);
        try {
          setUser(await api.me());
        } catch (e) {
          // Yalnız sunucu anahtarı reddettiyse oturum silinir; çevrimdışıyken misafirin anahtarı (= verisi) korunur
          if (e instanceof ApiError && e.status === 401) { await signOut(); await startGuest(); }
        }
      } else {
        await startGuest();
      }
      booting = false;
      setReady(true);
    })();
    return () => setUnauthorizedHandler(null);
  }, [signOut, startGuest]);

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
    upgrade: async (email, password, fullName) => {
      const r = await api.upgrade(email.trim(), password, fullName?.trim());
      await start(r.access_token, r.user);
    },
    // Çıkıştan sonra uygulama boş kalmasın: yeni bir misafir açılır
    logout: async () => { await signOut(); await startGuest(); },
    startSession: r => start(r.access_token, r.user),
    deleteAccount: async password => { await api.deleteAccount(password); await signOut(); await startGuest(); },
  }), [user, ready, start, signOut, startGuest]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth, AuthProvider içinde kullanılmalı');
  return ctx;
}
