import { useEffect, useState } from 'react';
import { ActivityIndicator, Image, View } from 'react-native';
import { Text } from './Text';

import { useTheme } from '@/components/ui';
import { getApiToken } from '@/lib/api';

/** Oturum gerektiren (onay bekleyen) fotoğraf: XHR ile indirilip data adresi olarak gösterilir. Hata olursa nedenini yazar. */
export default function AuthImage({ url, width, height }: { url: string; width: number; height: number }) {
  const t = useTheme();
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const xhr = new XMLHttpRequest();
    xhr.open('GET', url);
    xhr.responseType = 'blob';
    const token = getApiToken();
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.timeout = 30000;
    xhr.onload = () => {
      if (xhr.status < 200 || xhr.status >= 300) { setError(`Fotoğraf açılamadı (${xhr.status})`); return; }
      const reader = new FileReader();
      reader.onloadend = () => (typeof reader.result === 'string' ? setSrc(reader.result) : setError('Fotoğraf okunamadı'));
      reader.onerror = () => setError('Fotoğraf okunamadı');
      reader.readAsDataURL(xhr.response);
    };
    xhr.onerror = xhr.ontimeout = () => setError('Fotoğraf indirilemedi (sunucuya ulaşılamadı)');
    xhr.send();
    return () => xhr.abort();
  }, [url]);

  return (
    <View style={{ width, height, borderRadius: 12, overflow: 'hidden', backgroundColor: t.tintSoft, alignItems: 'center', justifyContent: 'center', padding: 8 }}>
      {src ? <Image source={{ uri: src }} style={{ width, height }} resizeMode="cover" />
        : error ? <Text style={{ color: t.danger, textAlign: 'center' }}>{error}</Text>
        : <ActivityIndicator color={t.tint} />}
    </View>
  );
}
