import { useState } from 'react';
import { Image, Text, View } from 'react-native';

/** Ürün fotoğrafı (marketfiyati); yoksa ya da açılmazsa kategori simgesi */
export default function ProductImage({ uri, icon, size = 52 }: { uri: string | null | undefined; icon: string; size?: number }) {
  const [failed, setFailed] = useState(false);
  if (!uri || failed) {
    return (
      <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
        <Text style={{ fontSize: size * 0.65 }}>{icon}</Text>
      </View>
    );
  }
  return (
    <Image source={{ uri }} onError={() => setFailed(true)} resizeMode="contain"
      style={{ width: size, height: size, borderRadius: 8, backgroundColor: '#fff' }} />
  );
}
