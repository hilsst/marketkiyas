/** Türkçe para biçimi: "1.234,50" (binlik nokta, ondalık virgül). Hermes'te Intl'e güvenmemek için elle yazıldı. */
export function formatTL(value: number | null | undefined, digits = 2): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return digits > 0 ? `0,${'0'.repeat(digits)}` : '0';
  const [int, frac] = Math.abs(n).toFixed(digits).split('.');
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  const sign = n < 0 && Number(`${int}.${frac ?? '0'}`) !== 0 ? '-' : '';
  return `${sign}${grouped}${frac ? ',' + frac : ''}`;
}

/**
 * Birim fiyat etiketi: ml → "₺/lt", g → "₺/kg". Miktar ya da birim yoksa (ya da adet ise) null döner:
 * yanlış bir ₺/kg göstermektense hiç göstermemek tercih edilir.
 */
export function unitPriceLabel(price: number | null | undefined, quantity: string | number | null | undefined, unit: string | null | undefined): string | null {
  const p = Number(price);
  const q = Number(quantity);
  if (price == null || quantity == null || !Number.isFinite(p) || !Number.isFinite(q) || q <= 0 || p <= 0) return null;
  if (unit === 'ml') return `${formatTL((p / q) * 1000)} ₺/lt`;
  if (unit === 'g') return `${formatTL((p / q) * 1000)} ₺/kg`;
  return null;
}
