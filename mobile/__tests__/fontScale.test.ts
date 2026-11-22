import { FONT_SIZES, scaleOf } from '@/lib/fontScale';

describe('fontScale', () => {
  it('seçime göre çarpan', () => {
    expect(scaleOf('normal')).toBe(1);
    expect(scaleOf('large')).toBe(1.15);
    expect(scaleOf('xlarge')).toBe(1.3);
  });
  it('bilinmeyen ya da boş değer normal sayılır', () => {
    expect(scaleOf(null)).toBe(1);
    expect(scaleOf('x')).toBe(1);
    expect(FONT_SIZES).toHaveLength(3);
  });
});
