import { scaleAmount } from '@/lib/amount';

describe('scaleAmount', () => {
  it('çarpan 1 ise metne dokunmaz', () => expect(scaleAmount('2 yemek kaşığı', 1)).toBe('2 yemek kaşığı'));
  it('sayıyı ölçekler', () => {
    expect(scaleAmount('500 g', 1.5)).toBe('750 g');
    expect(scaleAmount('4 adet', 3)).toBe('12 adet');
  });
  it('kesirleri ölçekler', () => {
    expect(scaleAmount('1/2 demet', 2)).toBe('1 demet');
    expect(scaleAmount('1 adet', 0.5)).toBe('½ adet');
    expect(scaleAmount('1 1/2 su bardağı', 2)).toBe('3 su bardağı');
  });
  it('sayısı olmayan miktarı olduğu gibi bırakır', () => expect(scaleAmount('tutam', 2)).toBe('tutam'));
});
