import type { User } from '@/lib/api';

/** Misafir: hesapsız başladı. Kaydetme ve paylaşma anında e-posta ile hesaba çevrilir (/login?upgrade=1). */
export const isGuest = (user: User | null | undefined): boolean => !!user?.is_guest;

export type AccountReason = 'share' | 'join' | 'family' | 'save' | 'plan';

export const ACCOUNT_REASON_TEXT: Record<AccountReason, string> = {
  share: 'Listenizi başkalarıyla paylaşmak için ücretsiz hesap açın. Listeleriniz ve planlarınız olduğu gibi kalır.',
  join: 'Ortak listeye katılmak için ücretsiz hesap açın. Şu anki listeleriniz ve planlarınız kaybolmaz.',
  family: 'Aile üyeleriyle liste paylaşmak için ücretsiz hesap açın. Listeleriniz ve planlarınız olduğu gibi kalır.',
  save: 'Tasarrufunuzu kaydetmek ve her ay görmek için ücretsiz hesap açın. Listeleriniz ve planlarınız olduğu gibi kalır.',
  plan: 'Planınız bu telefonda duruyor. Hesap açarsanız yeni telefonda da bulursunuz, başkasıyla paylaşabilirsiniz.',
};

/** Hesap gereken bir eylem öncesi: misafirse hesap açma ekranının adresini, değilse null döner. */
export function accountRedirect(user: User | null | undefined, reason: AccountReason) {
  if (!user) return { pathname: '/login' as const, params: { reason } };
  if (!user.is_guest) return null;
  return { pathname: '/login' as const, params: { upgrade: '1', reason } };
}
