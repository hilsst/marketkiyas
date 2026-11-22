import { ApiError } from '@/lib/api';

export const GENERIC_ERROR = 'Bir sorun oldu. Biraz sonra tekrar deneyin.';

/**
 * Kullanıcıya gösterilecek hata metni. Bağlantı hatası (status 0) ve Türkçe sunucu mesajları olduğu gibi geçer;
 * teknik kod ("İstek başarısız (500)"), İngilizce doğrulama metni ya da sunucu hatası sade cümleye çevrilir.
 */
export function friendlyError(e: unknown): string {
  const msg = e instanceof Error ? e.message : '';
  const status = e instanceof ApiError ? e.status : undefined;
  if (status === 0) return msg || 'Sunucuya ulaşılamadı. İnternet bağlantınızı kontrol edin.';
  const turkish = /[çğıöşüÇĞİÖŞÜ]/.test(msg);
  if (status === 422) return turkish ? msg : 'Bilgileri kontrol edin (örneğin e-posta adresi geçerli mi?).';
  if (status != null && status >= 500) return turkish && !/İstek başarısız/.test(msg) ? msg : GENERIC_ERROR;
  if (!msg || /İstek başarısız|\(\d{3}\)|Network request failed|Failed to fetch/i.test(msg)) return GENERIC_ERROR;
  // Türkçe harf içermeyen uzun metin büyük olasılıkla İngilizce teknik mesajdır
  if (!turkish && /[a-z]{4,} [a-z]{3,}/i.test(msg) && status !== 400 && status !== 401) return GENERIC_ERROR;
  return msg;
}
