/** Türkçe para biçimi: "1.234,50" (binlik nokta, ondalık virgül). Hermes'te Intl'e güvenmemek için elle yazıldı. */
export function formatTL(value: number | null | undefined, digits = 2): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return digits > 0 ? `0,${'0'.repeat(digits)}` : '0';
  const [int, frac] = Math.abs(n).toFixed(digits).split('.');
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  const sign = n < 0 && Number(`${int}.${frac ?? '0'}`) !== 0 ? '-' : '';
  return `${sign}${grouped}${frac ? ',' + frac : ''}`;
}
