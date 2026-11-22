import { ApiError } from '@/lib/api';
import { friendlyError, GENERIC_ERROR } from '@/lib/errors';

describe('friendlyError', () => {
  it('bağlantı hatası olduğu gibi geçer', () => {
    const m = 'Sunucuya ulaşılamadı. İnternet bağlantınızı kontrol edin.';
    expect(friendlyError(new ApiError(m, 0))).toBe(m);
  });
  it('sunucu hatası ve teknik kod sade cümleye döner', () => {
    expect(friendlyError(new ApiError('İstek başarısız (500)', 500))).toBe(GENERIC_ERROR);
    expect(friendlyError(new ApiError('Internal server error occurred', 404))).toBe(GENERIC_ERROR);
    expect(friendlyError(new Error('Network request failed'))).toBe(GENERIC_ERROR);
  });
  it('Türkçe 503 korunur, 422 doğrulama sade cümle olur', () => {
    expect(friendlyError(new ApiError('Fotoğraf işleme şu an kullanılamıyor.', 503))).toBe('Fotoğraf işleme şu an kullanılamıyor.');
    expect(friendlyError(new ApiError('value is not a valid email address', 422))).toMatch(/Bilgileri kontrol/);
  });
  it('Türkçe sunucu mesajı korunur', () => {
    expect(friendlyError(new ApiError('E-posta ya da şifre hatalı.', 401))).toBe('E-posta ya da şifre hatalı.');
  });
});
