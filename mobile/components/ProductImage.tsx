import { useState } from 'react';
import { Image, Text, View } from 'react-native';

import { useTheme } from '@/components/ui';

/** Ürün fotoğrafı (marketfiyati); yoksa ya da açılmazsa kategori simgesi. Yumuşak zeminli yuvarlak kare. */
export default function ProductImage({ uri, icon, size = 52 }: { uri: string | null | undefined; icon: string; size?: number }) {
  const t = useTheme();
  const [failed, setFailed] = useState(false);
  const box = { width: size, height: size, borderRadius: Math.round(size * 0.24), overflow: 'hidden' as const, alignItems: 'center' as const, justifyContent: 'center' as const };
  if (!uri || failed) {
    return (
      <View style={[box, { backgroundColor: t.tintSoft }]}>
        <Text style={{ fontSize: size * 0.5 }}>{icon}</Text>
      </View>
    );
  }
  return (
    <View style={[box, { backgroundColor: '#fff' }]}>
      <Image source={{ uri }} onError={() => setFailed(true)} resizeMode="contain" style={{ width: size, height: size }} />
    </View>
  );
}
