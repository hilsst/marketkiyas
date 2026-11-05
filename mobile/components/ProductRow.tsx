import { Pressable, Text, View } from 'react-native';

import MarketBadge from '@/components/MarketBadge';
import ProductImage from '@/components/ProductImage';
import { Muted, useTheme } from '@/components/ui';
import { formatSize, GroupSummary, MarketPrice, num } from '@/lib/api';
import { useCatalog } from '@/lib/catalog';
import { formatTL } from '@/lib/format';

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
        flexDirection: 'row', gap: 12, alignItems: 'center', padding: 12, borderRadius: 20,
        backgroundColor: t.card, opacity: pressed ? 0.75 : 1,
        shadowColor: t.shadow, shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 3 }, elevation: 2,
      })}>
      <ProductImage uri={group.image_url} icon={categoryIcon(group.category_id)} size={64} />
      <View style={{ flex: 1, gap: 3 }}>
        <Text style={{ color: t.text, fontWeight: '700', fontSize: 15 }} numberOfLines={2}>{group.name}</Text>
        <Muted>{[formatSize(group.quantity, group.unit), shown.length + ' market'].filter(Boolean).join(' · ')}</Muted>
        {cheapest && (
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
            <MarketBadge id={cheapest.market_id} size={20} />
            <Muted style={{ fontSize: 13 }}>{marketById(cheapest.market_id)?.name} · en ucuz</Muted>
          </View>
        )}
      </View>
      {cheapest && (
        <View style={{ alignItems: 'flex-end', gap: 4 }}>
          <Text style={{ color: t.tintDark, fontWeight: '800', fontSize: 18, fontVariant: ['tabular-nums'] }}>{formatTL(num(cheapest.min_price))} ₺</Text>
          {cheapest.regular_price && (
            <Text style={{ fontSize: 12, color: '#fff', backgroundColor: t.accent, fontWeight: '800', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, overflow: 'hidden' }}>İNDİRİM</Text>
          )}
        </View>
      )}
    </Pressable>
  );
}
