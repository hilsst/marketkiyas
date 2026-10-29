import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { api, Category, Market } from '@/lib/api';

interface CatalogState {
  markets: Market[];
  marketById: (id: number | null | undefined) => Market | undefined;
  categories: Category[]; // yalnızca üst kategoriler
  categoryById: (id: number | null | undefined) => Category | undefined;
  subcategoriesOf: (id: number) => Category[]; // sunucu en kalabalığı önce verir
  categoryIcon: (id: number | null | undefined) => string;
}

const CatalogContext = createContext<CatalogState | null>(null);

/** Market ve kategori listeleri uygulama açılışında bir kez yüklenir; her ekran buradan okur. */
export function CatalogProvider({ children }: { children: ReactNode }) {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [all, setAll] = useState<Category[]>([]);

  useEffect(() => {
    api.markets().then(setMarkets).catch(() => {});
    api.categories().then(setAll).catch(() => {});
  }, []);

  const marketMap = useMemo(() => new Map(markets.map(m => [m.id, m])), [markets]);
  const categoryMap = useMemo(() => new Map(all.map(c => [c.id, c])), [all]);
  const categoryById = useCallback((id: number | null | undefined) => (id == null ? undefined : categoryMap.get(id)), [categoryMap]);

  const value = useMemo<CatalogState>(() => ({
    markets,
    marketById: id => (id == null ? undefined : marketMap.get(id)),
    categories: all.filter(c => c.parent_id == null),
    categoryById,
    subcategoriesOf: id => all.filter(c => c.parent_id === id),
    categoryIcon: id => categoryById(id)?.icon || '🛒',
  }), [markets, marketMap, all, categoryById]);

  return <CatalogContext.Provider value={value}>{children}</CatalogContext.Provider>;
}

export function useCatalog(): CatalogState {
  const ctx = useContext(CatalogContext);
  if (!ctx) throw new Error('useCatalog, CatalogProvider içinde kullanılmalı');
  return ctx;
}
