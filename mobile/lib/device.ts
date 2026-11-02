import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

// Cihaza özgü rastgele kimlik: analitikte misafir de bir kişi sayılır. Kişisel veri taşımaz;
// Oturum anahtarından ayrı tutulur (çıkış yapınca silinmez); iOS'ta Anahtar Zinciri uygulama silinse de
// kalabilir. Hesap silinince sunucu bu cihazın olaylarını siler. Kişisel veri içermez.
const KEY = 'ucuzu.device_id';

let cached: string | null = null;

/** İstekler başlık olarak taşır (lib/api.ts); açılışta initDeviceId bitene kadar boştur. */
export function getDeviceId(): string | null { return cached; }
export function setDeviceId(id: string | null) { cached = id; }

export function newDeviceId(random: () => number = Math.random): string {
  const hex = (n: number) => Array.from({ length: n }, () => Math.floor(random() * 16).toString(16)).join('');
  return `${hex(8)}-${hex(4)}-4${hex(3)}-${(8 + Math.floor(random() * 4)).toString(16)}${hex(3)}-${hex(12)}`;
}

async function read(): Promise<string | null> {
  if (Platform.OS === 'web') {
    try { return globalThis.localStorage?.getItem(KEY) ?? null; } catch { return null; }
  }
  return SecureStore.getItemAsync(KEY);
}

async function write(id: string): Promise<void> {
  if (Platform.OS === 'web') {
    try { globalThis.localStorage?.setItem(KEY, id); } catch { /* gizli pencere */ }
    return;
  }
  await SecureStore.setItemAsync(KEY, id);
}

/** Kayıtlı kimliği okur, yoksa üretip saklar. Hata verirse bu açılış için bellekte kalır. */
export async function initDeviceId(): Promise<string> {
  if (cached) return cached;
  let id: string | null = null;
  try { id = await read(); } catch { /* okunamadı: yenisi üretilir */ }
  if (!id) {
    id = newDeviceId();
    try { await write(id); } catch { /* bu açılışta bellekte kalır */ }
  }
  cached = id;
  return id;
}
