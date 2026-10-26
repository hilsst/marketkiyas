"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  api, getToken, setToken, setUnauthorizedHandler,
  Category, ListSummary, Market, User,
} from "./api";

// Giriş gerektirmeyen sayfalar: arama ve ürün detayı herkese açık
const PUBLIC_PATHS = ["/", "/login", "/deals"];
const isPublic = (path: string) => PUBLIC_PATHS.includes(path) || path.startsWith("/products/");

interface Ctx {
  user: User | null; hydrated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  markets: Market[]; marketById: (id: number | null | undefined) => Market | undefined;
  categories: Category[]; categoryById: (id: number | null | undefined) => Category | undefined;
  lists: ListSummary[]; refreshLists: () => Promise<void>;
  createList: (name: string) => Promise<number>;
  addItem: (listId: number, groupId: number, preferredProductId?: number | null) => Promise<void>;
  toast: string | null; setToast: (s: string | null) => void;
  unreadAlerts: number; refreshAlerts: () => Promise<void>;
}
const AppCtx = createContext<Ctx | null>(null);

export function ListProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [lists, setLists] = useState<ListSummary[]>([]);
  const [toast, setToast] = useState<string | null>(null);
  const [unreadAlerts, setUnreadAlerts] = useState(0);

  const refreshLists = useCallback(async () => {
    if (!getToken()) { setLists([]); return; }
    setLists(await api.lists());
  }, []);

  // Şube seçilince yeni zincirler (CarrefourSA, Migros…) eklenebilir; sayfa değişince market listesi tazelenir
  useEffect(() => {
    api.markets().then(setMarkets).catch(() => {});
  }, [pathname]);

  useEffect(() => {
    api.categories().then(setCategories).catch(() => {});
    setUnauthorizedHandler(() => { setUser(null); setLists([]); });
    (async () => {
      if (getToken()) {
        try {
          setUser(await api.me());
          await refreshLists();
        } catch { setToken(null); }
      }
      setHydrated(true);
    })();
    return () => setUnauthorizedHandler(null);
  }, [refreshLists]);

  useEffect(() => {
    if (hydrated && !user && !isPublic(pathname)) {
      router.replace("/login?next=" + encodeURIComponent(pathname + window.location.search));
    }
  }, [hydrated, user, pathname, router]);

  // 🔔 rozeti: fiyatı düşen alarm sayısı. Sayı artınca (izin verildiyse) telefon bildirimi gösterilir.
  const refreshAlerts = useCallback(async () => {
    if (!getToken()) { setUnreadAlerts(0); return; }
    try {
      const { unread } = await api.unreadAlerts();
      setUnreadAlerts(prev => {
        if (unread > prev && typeof Notification !== "undefined" && Notification.permission === "granted") {
          try { new Notification("MarketKıyas", { body: "Takip ettiğiniz bir ürünün fiyatı düştü 🔔" }); } catch {}
        }
        return unread;
      });
    } catch {}
  }, []);

  useEffect(() => {
    if (!user) { setUnreadAlerts(0); return; }
    refreshAlerts();
    const t = setInterval(refreshAlerts, 5 * 60 * 1000);
    return () => clearInterval(t);
  }, [user, pathname, refreshAlerts]);

  useEffect(() => {
    if (toast) { const t = setTimeout(() => setToast(null), 2200); return () => clearTimeout(t); }
  }, [toast]);

  const onAuth = async (res: { access_token: string; user: User }) => {
    setToken(res.access_token);
    setUser(res.user);
    await refreshLists();
  };
  const login = async (email: string, password: string) => onAuth(await api.login(email, password));
  const register = async (email: string, password: string, fullName?: string) =>
    onAuth(await api.register(email, password, fullName));
  const logout = () => { setToken(null); setUser(null); setLists([]); router.push("/login"); };

  const createList = async (name: string) => {
    const created = await api.createList(name);
    await refreshLists();
    return created.id;
  };

  // Grup listede varsa API miktarı artırır ve seçilen ürünü kilitler (demodaki davranış)
  const addItem = async (listId: number, groupId: number, preferredProductId: number | null = null) => {
    await api.addItem(listId, groupId, preferredProductId);
    await refreshLists();
  };

  const marketMap = useMemo(() => new Map(markets.map(m => [m.id, m])), [markets]);
  const categoryMap = useMemo(() => new Map(categories.map(c => [c.id, c])), [categories]);
  const marketById = useCallback((id: number | null | undefined) => (id == null ? undefined : marketMap.get(id)), [marketMap]);
  const categoryById = useCallback((id: number | null | undefined) => (id == null ? undefined : categoryMap.get(id)), [categoryMap]);

  return (
    <AppCtx.Provider value={{
      user, hydrated, login, register, logout,
      markets, marketById, categories, categoryById,
      lists, refreshLists, createList, addItem, toast, setToast, unreadAlerts, refreshAlerts,
    }}>
      {children}
      {toast && (
        <div className="fixed bottom-20 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-sm px-4 py-2 rounded-full shadow-lg z-50">
          {toast}
        </div>
      )}
    </AppCtx.Provider>
  );
}
export function useLists() {
  const c = useContext(AppCtx);
  if (!c) throw new Error("useLists inside ListProvider");
  return c;
}

/** Ürün grubu ikonu: API'de grup emojisi yok, kategorinin ikonu kullanılır. */
export function useGroupIcon() {
  const { categoryById } = useLists();
  return (categoryId: number | null | undefined) => categoryById(categoryId)?.icon || "🛒";
}
