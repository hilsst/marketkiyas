import { useState } from 'react';
import { Image, View } from 'react-native';

import FoodIcon from '@/components/FoodIcon';
import { useTheme } from '@/components/ui';
import { API_URL } from '@/lib/api';
import type { FoodGlyph } from '@/lib/icons';

/** Sunucu göreli yol ("/media/recipes/x.jpg") ya da tam adres verebilir */
export function resolveImageUrl(uri: string): string {
  return /^https?:\/\//.test(uri) ? uri : `${API_URL}${uri.startsWith('/') ? '' : '/'}${uri}`;
}

/** Yemek fotoğrafı; yoksa ya da açılmazsa yemek türü simgesi (yumuşak zeminde). */
export default function RecipeImage({ uri, icon, width, height, radius = 10, iconSize }: {
  uri: string | null | undefined; icon: FoodGlyph; width: number; height?: number; radius?: number; iconSize?: number;
}) {
  const t = useTheme();
  const [failed, setFailed] = useState(false);
  const h = height ?? width;
  const box = { width, height: h, borderRadius: radius, overflow: 'hidden' as const, alignItems: 'center' as const, justifyContent: 'center' as const, backgroundColor: t.tintSoft };
  return (
    <View style={box}>
      {uri && !failed ? (
        <Image source={{ uri: resolveImageUrl(uri) }} onError={() => setFailed(true)} resizeMode="cover" style={{ width, height: h }} accessibilityIgnoresInvertColors />
      ) : (
        <FoodIcon name={icon} size={iconSize ?? Math.round(Math.min(width, h) * 0.5)} />
      )}
    </View>
  );
}
