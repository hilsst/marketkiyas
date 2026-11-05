import { formatTL } from '@/lib/format';

describe('formatTL', () => {
  it('ondalık virgül, binlik nokta', () => {
    expect(formatTL(32.5)).toBe('32,50');
    expect(formatTL(1234.5)).toBe('1.234,50');
    expect(formatTL(1234567.891)).toBe('1.234.567,89');
  });
  it('basamak sayısı ve sıfır', () => {
    expect(formatTL(1999.6, 0)).toBe('2.000');
    expect(formatTL(0)).toBe('0,00');
  });
  it('geçersiz değer 0 olur, negatif işaret korunur', () => {
    expect(formatTL(null)).toBe('0,00');
    expect(formatTL(undefined)).toBe('0,00');
    expect(formatTL(NaN)).toBe('0,00');
    expect(formatTL(-12.5)).toBe('-12,50');
  });
});
