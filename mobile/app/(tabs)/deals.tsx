import { router, useFocusEffect } from 'expo-router';
import { useCallback, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';

import MarketBadge from '@/components/MarketBadge';
import ProductImage from '@/components/ProductImage';
import { Card, Muted, Screen, Title, useTheme } from '@/components/ui';
import { api, Deal, formatSize, num } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { useCatalog } from '@/lib/catalog';

/** Fırsatlar: son 30 güne göre ucuzlayan ya da kampanyadaki ürünler; market ve kategoriye göre süzülür. */
export default function DealsScreen() {
  const t = useTheme();
  const { user } = useAuth();
  const { marketById, categories, categoryIcon } = useCatalog();
  const [deals, setDeals] = useState<Deal[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [market, setMarket] = useState<number | null>(null); // null = tüm marketler
  const [cat, setCat] = useState<number | null>(null);

  useFocusEffect(useCallback(() => {
    api.deals().then(d => { setDeals(d); setError(null); }).catch(e => setError((e as Error).message));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- giriş yapınca seçili marketlere göre yeniden yüklenir
  }, [user]));

  const marketIds = useMemo(() => Array.from(new Set((deals || []).map(d => d.market_id))), [deals]);
  const catIds = useMemo(() => new Set((deals || []).map(d => d.category_id)), [deals]);
  const shown = (deals || []).filter(d => (market == null || d.market_id === market) && (cat == null || d.category_id === cat));

  const chip = (key: string, active: boolean, onPress: () => void, label: React.ReactNode) => (
    <Pressable key={key} onPress={onPress} style={{ flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 7,
      borderRadius: 999, borderWidth: 1, borderColor: active ? t.tint : t.border, backgroundColor: active ? t.tint : t.card }}>
      {label}
    </Pressable>
  );
  const chipText = (active: boolean, text: string) => <Text style={{ color: active ? '#fff' : t.text, fontSize: 13, fontWeight: '600' }}>{text}</Text>;

  return (
    <Screen>
      <Title>🏷️ Fırsatlar</Title>
      <Muted>{user ? 'Seçtiğin marketlerde' : 'Marketlerde'} son 30 güne göre ucuzlayan ve kampanyadaki ürünler.</Muted>

      {marketIds.length > 1 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginHorizontal: -16 }} contentContainerStyle={{ paddingHorizontal: 16, gap: 8 }}>
          {chip('all', market == null, () => setMarket(null), chipText(market == null, 'Tüm marketler'))}
          {marketIds.map(id => chip(String(id), market === id, () => setMarket(id),
            <><MarketBadge id={id} size={18} />{chipText(market === id, marketById(id)?.name || '')}</>))}
        </ScrollView>
      )}
      {catIds.size > 1 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginHorizontal: -16 }} contentContainerStyle={{ paddingHorizontal: 16, gap: 8 }}>
          {chip('all', cat == null, () => setCat(null), chipText(cat == null, 'Tümü'))}
          {categories.filter(c => catIds.has(c.id)).map(c => chip(String(c.id), cat === c.id, () => setCat(c.id),
            chipText(cat === c.id, `${c.icon || ''} ${c.name}`.trim())))}
        </ScrollView>
      )}

      {error && <Card><Text style={{ color: t.danger }}>Fırsatlar yüklenemedi: {error}</Text></Card>}
      {deals === null && !error && <ActivityIndicator color={t.tint} style={{ marginTop: 24 }} />}
      {deals?.length === 0 && (
        <Card style={{ alignItems: 'center', gap: 6, padding: 24 }}>
          <Text style={{ fontSize: 30 }}>🏷️</Text>
          <Text style={{ color: t.text }}>Şu an indirimde ürün yok</Text>
          <Muted>Fiyatlar her güncellendiğinde bu sayfa yenilenir.</Muted>
        </Card>
      )}

      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10 }}>
        {shown.map(d => (
          <Pressable key={d.group_id} style={{ width: '48%', flexGrow: 1 }}
            onPress={() => router.push({ pathname: '/product/[id]', params: { id: String(d.group_id) } })}>
            <Card style={{ gap: 6, padding: 12, flex: 1 }}>
              <Text style={{ position: 'absolute', top: 8, right: 8, zIndex: 1, backgroundColor: '#ef4444', color: '#fff',
                fontSize: 11, fontWeight: '800', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, overflow: 'hidden' }}>%{d.discount_percent}</Text>
              <View style={{ alignItems: 'center' }}><ProductImage uri={d.image_url} icon={categoryIcon(d.category_id)} size={70} /></View>
              <Text style={{ color: t.text, fontSize: 13, fontWeight: '600', minHeight: 34 }} numberOfLines={2}>{d.group_name}</Text>
              <Text style={{ color: t.textMuted, fontSize: 11 }} numberOfLines={1}>{[d.brand, formatSize(d.quantity, d.unit)].filter(Boolean).join(' · ')}</Text>
              <View style={{ marginTop: 'auto', gap: 2 }}>
                <Text style={{ color: t.textMuted, fontSize: 11, textDecorationLine: 'line-through' }}>{num(d.previous_price).toFixed(2)} ₺</Text>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <MarketBadge id={d.market_id} size={18} />
                  <Text style={{ color: t.tint, fontWeight: '800', fontSize: 15 }}>{num(d.price).toFixed(2)} ₺</Text>
                </View>
                {d.is_campaign && <Text style={{ color: '#ea580c', fontSize: 10, fontWeight: '700' }}>KAMPANYA</Text>}
              </View>
            </Card>
          </Pressable>
        ))}
      </View>
    </Screen>
  );
}
