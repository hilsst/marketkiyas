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
