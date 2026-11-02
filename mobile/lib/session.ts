import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

// Oturum anahtarı (JWT): telefonda şifreli depoda, web önizlemesinde localStorage'da
const KEY = 'marketkiyas.token';

export async function loadToken(): Promise<string | null> {
  if (Platform.OS === 'web') {
    try { return globalThis.localStorage?.getItem(KEY) ?? null; } catch { return null; }
  }
  return SecureStore.getItemAsync(KEY);
}

export async function saveToken(token: string | null): Promise<void> {
  if (Platform.OS === 'web') {
    try {
      if (token) globalThis.localStorage?.setItem(KEY, token);
      else globalThis.localStorage?.removeItem(KEY);
    } catch { /* gizli pencere: oturum yalnız bu açılışta kalır */ }
    return;
  }
  if (token) await SecureStore.setItemAsync(KEY, token);
  else await SecureStore.deleteItemAsync(KEY);
}

// Küçük tercihler (ör. haftalık bildirim açık mı): token gibi saklanır
export async function loadFlag(key: string): Promise<string | null> {
  if (Platform.OS === 'web') {
    try { return globalThis.localStorage?.getItem(key) ?? null; } catch { return null; }
  }
  return SecureStore.getItemAsync(key);
}

export async function saveFlag(key: string, value: string | null): Promise<void> {
  if (Platform.OS === 'web') {
    try {
      if (value) globalThis.localStorage?.setItem(key, value);
      else globalThis.localStorage?.removeItem(key);
    } catch { /* yok say */ }
    return;
  }
  if (value) await SecureStore.setItemAsync(key, value);
  else await SecureStore.deleteItemAsync(key);
}
