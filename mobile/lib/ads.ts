/**
 * Reklam kuralları (Faz Planı v2, karar 2): yalnız iki yer, plan/liste/alışveriş/pişirme ekranlarında hiç.
 * AppLovin MAX native reklamı 2a'da bu iki yere bağlanır; şimdilik etiketli test kartı çizilir.
 *
 * EXPO_PUBLIC_ADS=off ile tamamen kapatılır (varsayılan: test).
 */
export type AdPlacement = 'home-top' | 'product-list';

/** Ürün listelerinde her kaç üründen sonra reklam */
export const AD_EVERY = 8;

export function adsEnabled(flag: string | undefined = process.env.EXPO_PUBLIC_ADS): boolean {
  return (flag ?? 'test').toLowerCase() !== 'off';
}

export type WithAd<T> = { kind: 'item'; item: T } | { kind: 'ad'; key: string };

/** Her `every` üründen sonra bir reklam yeri koyar; listenin sonuna reklam eklenmez. */
export function interleaveAds<T>(items: T[], every: number = AD_EVERY, enabled: boolean = adsEnabled()): WithAd<T>[] {
  const out: WithAd<T>[] = [];
  items.forEach((item, i) => {
    out.push({ kind: 'item', item });
    if (enabled && every > 0 && (i + 1) % every === 0 && i < items.length - 1) out.push({ kind: 'ad', key: `ad-${i}` });
  });
  return out;
}

/** Reklam görmemesi gereken ekranlar (çekirdek akış); Jest testi bunların reklam bileşenini içermediğini doğrular. */
export const AD_FREE_SCREENS = [
  'app/meals/index.tsx', 'app/meals/[id].tsx', 'app/meals/pantry.tsx', 'app/meals/deals.tsx',
  'app/recipe/[id].tsx', 'app/cook/[id].tsx', 'app/list/[id].tsx', 'app/(tabs)/lists.tsx',
] as const;
