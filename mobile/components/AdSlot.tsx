import { Text, View } from 'react-native';

import { useTheme } from '@/components/ui';
import { adsEnabled, AdPlacement } from '@/lib/ads';

export type { AdPlacement };

/**
 * Native reklam yeri. Yalnız iki yerleşim vardır: ana sayfa üstü ("home-top") ve ürün listelerinde
 * her 8 üründe bir ("product-list"). Plan, liste, alışveriş ve pişirme ekranlarına konmaz (bkz. lib/ads.ts).
 * 2a'da AppLovin MAX native birimi buraya bağlanır; şimdilik "Reklam (test)" etiketli yer tutucu çizilir.
 */
export default function AdSlot({ placement }: { placement: AdPlacement }) {
  const t = useTheme();
  if (!adsEnabled()) return null;
  return (
    <View testID={`ad-${placement}`} accessibilityLabel="Reklam"
      style={{ borderRadius: 14, borderWidth: 1, borderStyle: 'dashed', borderColor: t.border, backgroundColor: t.card,
        padding: 12, gap: 2, minHeight: placement === 'home-top' ? 64 : 80, justifyContent: 'center' }}>
      <Text style={{ color: t.textMuted, fontSize: 10, fontWeight: '700' }}>REKLAM · TEST</Text>
      <Text style={{ color: t.textMuted, fontSize: 12 }}>Burada AppLovin MAX native reklamı gösterilecek.</Text>
    </View>
  );
}
