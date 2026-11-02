/** Fiyat güveni: fiyatın ne kadar taze olduğu. Sunucu 7 günden eski şube fiyatını zaten kullanmaz; zincir geneli fiyat eski kalabilir. */
export const STALE_AFTER_DAYS = 7;

export interface Freshness { label: string; stale: boolean; days: number }

const dayStart = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();

export function priceFreshness(iso: string | null | undefined, now = new Date()): Freshness | null {
  if (!iso) return null;
  const at = new Date(iso);
  if (isNaN(at.getTime())) return null;
  const days = Math.max(0, Math.round((dayStart(now) - dayStart(at)) / 86400000));
  const time = at.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
  const label = days === 0 ? `bugün ${time}` : days === 1 ? `dün ${time}` : `${days} gün önce`;
  return { label, stale: days >= STALE_AFTER_DAYS, days };
}

/** "Bu fiyat yanlış" formundaki fiyat metnini ("45,50") sayıya çevirir; boş/geçersizse null. */
export function parseReportedPrice(text: string): number | null {
  const n = Number(text.trim().replace(',', '.'));
  return text.trim() && isFinite(n) && n > 0 && n <= 1_000_000 ? Math.round(n * 100) / 100 : null;
}
