import { parseReportedPrice, priceFreshness, STALE_AFTER_DAYS } from '@/lib/trust';

const now = new Date(2026, 10, 2, 15, 0); // 2 Kasım 2026 15:00 (yerel saat)
const at = (daysAgo: number, h = 9, m = 15) => new Date(2026, 10, 2 - daysAgo, h, m).toISOString();

describe('priceFreshness', () => {
  it('labels today, yesterday and older prices', () => {
    expect(priceFreshness(at(0), now)).toMatchObject({ days: 0, stale: false });
    expect(priceFreshness(at(0), now)!.label).toMatch(/^bugün \d\d[:.]\d\d$/);
    expect(priceFreshness(at(1), now)!.label).toMatch(/^dün /);
    expect(priceFreshness(at(3), now)).toEqual({ label: '3 gün önce', stale: false, days: 3 });
  });

  it('warns once a price is a week old', () => {
    expect(priceFreshness(at(STALE_AFTER_DAYS - 1), now)!.stale).toBe(false);
    expect(priceFreshness(at(STALE_AFTER_DAYS), now)!.stale).toBe(true);
    expect(priceFreshness(at(20), now)!.label).toBe('20 gün önce');
  });

  it('returns null for missing or broken dates and never goes negative', () => {
    expect(priceFreshness(null, now)).toBeNull();
    expect(priceFreshness('', now)).toBeNull();
    expect(priceFreshness('bozuk', now)).toBeNull();
    expect(priceFreshness(new Date(2026, 10, 3).toISOString(), now)!.days).toBe(0);
  });
});

describe('parseReportedPrice', () => {
  it('accepts Turkish and plain decimals', () => {
    expect(parseReportedPrice('45,50')).toBe(45.5);
    expect(parseReportedPrice(' 45.5 ')).toBe(45.5);
    expect(parseReportedPrice('7')).toBe(7);
  });
  it('rejects empty, zero, negative and non-numbers', () => {
    for (const bad of ['', '  ', '0', '-3', 'abc', '1e9']) expect(parseReportedPrice(bad)).toBeNull();
  });
});
