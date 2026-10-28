import { Pressable, Text, View } from 'react-native';

import MarketBadge from '@/components/MarketBadge';
import ProductImage from '@/components/ProductImage';
import { Muted, useTheme } from '@/components/ui';
import { formatSize, GroupSummary, MarketPrice, num } from '@/lib/api';
import { useCatalog } from '@/lib/catalog';

export const cheapestOf = (prices: MarketPrice[]) => [...prices].sort((a, b) => num(a.min_price) - num(b.min_price))[0];

/** Arama ve kategori listelerindeki ürün satırı: fotoğraf, ad, boyut, en ucuz market ve fiyat */
export default function ProductRow({ group, prices, onPress }: {
  group: GroupSummary; prices?: MarketPrice[]; onPress?: () => void;
}) {
  const t = useTheme();
  const { marketById, categoryIcon } = useCatalog();
  const shown = prices ?? group.market_prices; // market filtresi açıksa yalnız o marketler
  const cheapest = cheapestOf(shown);
  return (
    <Pressable onPress={onPress} accessibilityRole="button"
      style={({ pressed }) => ({
        flexDirection: 'row', gap: 12, alignItems: 'center', padding: 14, borderRadius: 16, borderWidth: 1,
        backgroundColor: t.card, borderColor: t.border, opacity: pressed ? 0.7 : 1,
      })}>
      <ProductImage uri={group.image_url} icon={categoryIcon(group.category_id)} />
      <View style={{ flex: 1, gap: 3 }}>
        <Text style={{ color: t.text, fontWeight: '600', fontSize: 15 }} numberOfLines={2}>{group.name}</Text>
        <Muted>{[formatSize(group.quantity, group.unit), shown.length + ' market'].filter(Boolean).join(' · ')}</Muted>
        {cheapest && (
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
            <MarketBadge id={cheapest.market_id} size={20} />
            <Muted>{marketById(cheapest.market_id)?.name}</Muted>
            <Text style={{ color: t.tint, fontWeight: '800' }}>{num(cheapest.min_price).toFixed(2)} ₺</Text>
            {cheapest.regular_price && <Text style={{ fontSize: 10, color: '#c2410c', fontWeight: '700' }}>İNDİRİM</Text>}
          </View>
        )}
      </View>
      <Text style={{ color: t.textMuted, fontSize: 18 }}>›</Text>
    </Pressable>
  );
}
