import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from 'react';

import { loadFlag, saveFlag } from '@/lib/session';

/** Uygulama içi yazı boyutu: telefonun yazı boyutu ayarının ÜSTÜNE biner, onu kapatmaz. */
export type FontSizeKey = 'normal' | 'large' | 'xlarge';
export const FONT_SIZES: { key: FontSizeKey; label: string; scale: number }[] = [
  { key: 'normal', label: 'Normal', scale: 1 },
  { key: 'large', label: 'Büyük', scale: 1.15 },
  { key: 'xlarge', label: 'Çok büyük', scale: 1.3 },
];
const KEY = 'ucuzu.fontSize';

export function scaleOf(key: string | null | undefined): number {
  return FONT_SIZES.find(s => s.key === key)?.scale ?? 1;
}

type Ctx = { size: FontSizeKey; scale: number; setSize: (k: FontSizeKey) => void };
const FontScaleContext = createContext<Ctx>({ size: 'normal', scale: 1, setSize: () => {} });

export function FontScaleProvider({ children }: { children: ReactNode }) {
  const [size, setSizeState] = useState<FontSizeKey>('normal');
  useEffect(() => {
    loadFlag(KEY).then(v => { if (v && FONT_SIZES.some(s => s.key === v)) setSizeState(v as FontSizeKey); }).catch(() => {});
  }, []);
  const value = useMemo<Ctx>(() => ({
    size, scale: scaleOf(size),
    setSize: (k: FontSizeKey) => { setSizeState(k); saveFlag(KEY, k).catch(() => {}); },
  }), [size]);
  return <FontScaleContext.Provider value={value}>{children}</FontScaleContext.Provider>;
}

export function useFontScale(): Ctx {
  return useContext(FontScaleContext);
}
