import { Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Text, View } from 'react-native';

import MarketBadge from '@/components/MarketBadge';
import ProductImage from '@/components/ProductImage';
import { Card, Muted, Screen, useTheme } from '@/components/ui';
import { api, formatSize, GroupDetail, num } from '@/lib/api';
import { useCatalog } from '@/lib/catalog';

/**
 * Ürün sayfası: seçili şubelerdeki her fiyat ayrı satır (web'deki gibi "BİM · Karlıdağ").
 * Listeye ekleme ve fiyat alarmı 5. ve 7. adımlarda bu sayfaya eklenir.
 */
export default function ProductScreen() {
  const t = useTheme();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { marketById, categoryIcon, categoryById } = useCatalog();
  const [group, setGroup] = useState<GroupDetail | null | undefined>(undefined);

  useEffect(() => {
    api.productGroup(Number(id)).then(setGroup).catch(() => setGroup(null));
  }, [id]);

  const offers = useMemo(() => (group?.products ?? [])
    .filter(p => p.price != null)
    .flatMap(p => p.store_prices.length
      ? p.store_prices.map(sp => ({ key: `${p.id}-${sp.store_id}`, product: p, store: sp.store_name as string | null, price: num(sp.price) }))
      : [{ key: String(p.id), product: p, store: p.store_name, price: num(p.price) }])
    .sort((a, b) => a.price - b.price), [group]);

  if (group === undefined) return <Screen safeTop={false}><ActivityIndicator color={t.tint} style={{ marginTop: 40 }} /></Screen>;
  if (group === null) return <Screen safeTop={false}><Muted>Ürün bulunamadı.</Muted></Screen>;

  return (
    <Screen safeTop={false}>
      <Stack.Screen options={{ title: group.name }} />
      <Card style={{ flexDirection: 'row', gap: 14, alignItems: 'center' }}>
        <ProductImage uri={group.image_url} icon={categoryIcon(group.category_id)} size={80} />
        <View style={{ flex: 1, gap: 4 }}>
          <Text style={{ color: t.text, fontSize: 18, fontWeight: '800' }}>{group.name}</Text>
          <Muted>{[formatSize(group.quantity, group.unit), categoryById(group.category_id)?.name].filter(Boolean).join(' · ')}</Muted>
        </View>
      </Card>

      <Card style={{ padding: 0 }}>
        <Text style={{ color: t.text, fontWeight: '700', padding: 14 }}>
          {new Set(offers.map(o => o.product.market_id)).size} markette bulundu
        </Text>
        {offers.map((o, i) => (
          <View key={o.key} style={{ flexDirection: 'row', alignItems: 'center', gap: 10, padding: 14, borderTopWidth: 1, borderTopColor: t.border }}>
            <MarketBadge id={o.product.market_id} size={32} />
            <View style={{ flex: 1 }}>
              <Text style={{ color: t.text, fontWeight: '600' }} numberOfLines={1}>
                {marketById(o.product.market_id)?.name}{o.store ? ` · ${o.store}` : ''}
              </Text>
              <Muted>{o.product.brand ? `${o.product.brand} · ` : ''}{o.product.name}</Muted>
            </View>
            <View style={{ alignItems: 'flex-end' }}>
              <Text style={{ color: i === 0 ? t.tint : t.text, fontWeight: '800', fontSize: 16 }}>{o.price.toFixed(2)} ₺</Text>
              {i === 0 && <Text style={{ color: t.tint, fontSize: 10, fontWeight: '700' }}>EN UCUZ</Text>}
            </View>
          </View>
        ))}
      </Card>
    </Screen>
  );
}
