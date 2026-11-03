import * as Location from 'expo-location';

export interface Coords { lat: number; lon: number }
export type LocationResult = { coords: Coords; reason?: undefined } | { coords: null; reason: 'denied' | 'unavailable' | 'outside' };

const TTL_MS = 10 * 60 * 1000; // aynı oturumda konum 10 dakika yeniden kullanılır
let cached: { coords: Coords; at: number } | null = null;

/** Sunucu yalnız Türkiye sınırları içindeki koordinatı kabul eder (stores/nearby ile aynı) */
export const inTurkey = (c: Coords) => c.lat >= 35 && c.lat <= 43 && c.lon >= 25 && c.lon <= 45;

const withTimeout = <T,>(p: Promise<T>, ms: number) =>
  Promise.race([p, new Promise<never>((_, reject) => setTimeout(() => reject(new Error('timeout')), ms))]);

/**
 * Kullanıcının konumunu verir; izin yoksa bir kez sorar. Yalnız "uygulama açıkken" iznidir, arka planda
 * konum izlenmez. Konum sunucuya yalnız Yakın Market planı hesaplanırken gönderilir, kaydedilmez.
 */
export async function getCoords(): Promise<LocationResult> {
  if (cached && Date.now() - cached.at < TTL_MS) return { coords: cached.coords };
  try {
    let perm = await Location.getForegroundPermissionsAsync();
    if (!perm.granted && perm.canAskAgain) perm = await Location.requestForegroundPermissionsAsync();
    if (!perm.granted) return { coords: null, reason: 'denied' };
    const pos = (await Location.getLastKnownPositionAsync())
      ?? (await withTimeout(Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced }), 10000));
    const coords = { lat: pos.coords.latitude, lon: pos.coords.longitude };
    if (!inTurkey(coords)) return { coords: null, reason: 'outside' };
    cached = { coords, at: Date.now() };
    return { coords };
  } catch {
    return { coords: null, reason: 'unavailable' };
  }
}

/** İki nokta arası kuş uçuşu mesafe (km) */
export function distanceKm(a: Coords, b: Coords): number {
  const rad = (d: number) => (d * Math.PI) / 180;
  const h = Math.sin(rad(b.lat - a.lat) / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(rad(b.lon - a.lon) / 2) ** 2;
  return 12742 * Math.asin(Math.sqrt(h));
}

/** 0,4 km ya da 12 km */
export const formatKm = (km: number) => `${km < 10 ? km.toFixed(1).replace('.', ',') : Math.round(km)} km`;
