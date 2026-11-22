import { formatTL, unitPriceLabel } from '@/lib/format';

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

describe('unitPriceLabel', () => {
  it('ml ve g için litre/kg başına fiyat', () => {
    expect(unitPriceLabel(17.9, '500', 'ml')).toBe('35,80 ₺/lt');
    expect(unitPriceLabel(47.5, '1500', 'ml')).toBe('31,67 ₺/lt');
    expect(unitPriceLabel(22.5, '500', 'g')).toBe('45,00 ₺/kg');
  });
  it('miktar, birim ya da fiyat yoksa ve adet için null', () => {
    expect(unitPriceLabel(10, null, 'g')).toBeNull();
    expect(unitPriceLabel(10, '500', null)).toBeNull();
    expect(unitPriceLabel(10, '0', 'g')).toBeNull();
    expect(unitPriceLabel(null, '500', 'g')).toBeNull();
    expect(unitPriceLabel(10, '6', 'adet')).toBeNull();
  });
});
