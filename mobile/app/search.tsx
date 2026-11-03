import { router, useLocalSearchParams } from 'expo-router';
import { Fragment, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, TextInput, View } from 'react-native';

import AdSlot from '@/components/AdSlot';
import { AD_EVERY, adsEnabled, interleaveAds } from '@/lib/ads';
import ProductRow from '@/components/ProductRow';
import Icon from '@/components/Icon';
import { Chip, EmptyState, Muted, Screen, useTheme } from '@/components/ui';
import { api, GroupSummary, num } from '@/lib/api';
import { useCatalog } from '@/lib/catalog';

/** Ürün araması. Ana sayfadaki arama çubuğu buraya açılır. */
export default function SearchScreen() {
  const t = useTheme();
  // listId: liste ekranındaki 'Ürün ekle'den gelindiyse ürün doğrudan o listeye eklenir
  const params = useLocalSearchParams<{ q?: string; listId?: string }>();
  const [q, setQ] = useState(params.q ?? '');
  const [results, setResults] = useState<GroupSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { markets } = useCatalog();
  const [market, setMarket] = useState<number | null>(null); // yalnız bu marketin fiyatları
  const [cheapFirst, setCheapFirst] = useState(true);

  useEffect(() => {
    const term = q.trim();
    let cancelled = false;
    const timer = setTimeout(() => {
      if (!term) { setResults([]); return; }
      api.searchProducts(term)
        .then(r => { if (!cancelled) { setResults(r); setError(null); } })
        .catch(e => { if (!cancelled) setError(e.message); });
    }, 300);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [q]);

  const cheapest = (prices: GroupSummary['market_prices']) => Math.min(...prices.map(m => num(m.min_price)));
  const visible = (results ?? [])
    .map(g => ({ g, prices: market == null ? g.market_prices : g.market_prices.filter(m => m.market_id === market) }))
    .filter(x => x.prices.length > 0)
    .sort((a, b) => (cheapFirst ? cheapest(a.prices) - cheapest(b.prices) : 0));

  return (
    <Screen safeTop={false}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: t.card, borderRadius: 16, paddingHorizontal: 14,
        shadowColor: t.shadow, shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 3 }, elevation: 2 }}>
        <Icon name="search" size={20} color={t.textMuted} />
        <TextInput placeholder="Ürün ara (örn. süt, ekmek, deterjan)" placeholderTextColor={t.textMuted} value={q} onChangeText={setQ}
          autoFocus returnKeyType="search" autoCorrect={false}
          style={[{ flex: 1, color: t.text, fontSize: 16, paddingVertical: 14 }, { outlineStyle: 'none' } as object]} />
        {q !== '' && (
          <Pressable onPress={() => setQ('')} hitSlop={10} accessibilityLabel="Aramayı temizle"><Icon name="x-circle" size={20} color={t.textMuted} /></Pressable>
        )}
      </View>
      {q.trim() !== '' && results && results.length > 0 && (
        <>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginHorizontal: -18 }} contentContainerStyle={{ paddingHorizontal: 18, gap: 8 }}>
            <Chip label="En ucuz" on={cheapFirst} onPress={() => setCheapFirst(v => !v)} />
            <Chip label="Tüm marketler" on={market == null} onPress={() => setMarket(null)} />
            {markets.map(m => <Chip key={m.id} label={m.name} on={market === m.id} onPress={() => setMarket(market === m.id ? null : m.id)} />)}
          </ScrollView>
          <Muted>{visible.length} ürün</Muted>
        </>
      )}
      {error && <Text style={{ color: t.danger }}>{error}</Text>}
      {results === null && q.trim() !== '' && !error && <ActivityIndicator color={t.tint} style={{ marginTop: 24 }} />}
      {q.trim() === '' && <EmptyState icon="search" title="Ne arıyorsun?" text="Ürün adını yaz, yakınındaki marketlerin fiyatlarını karşılaştıralım." />}
      {q.trim() !== '' && results?.length === 0 && <EmptyState icon="search" title="Sonuç bulunamadı" text="Farklı bir yazım ya da daha kısa bir kelime dene." />}
      {/* Listeye ürün eklerken (listId) reklam gösterilmez: liste akışı temiz kalır */}
      {interleaveAds(visible, AD_EVERY, !params.listId && adsEnabled()).map(r => r.kind === 'ad'
        ? <AdSlot key={r.key} placement="product-list" />
        : <Fragment key={r.item.g.id}>
            <ProductRow group={r.item.g} prices={r.item.prices} onPress={() => router.push({ pathname: '/product/[id]', params: params.listId ? { id: String(r.item.g.id), listId: params.listId } : { id: String(r.item.g.id) } })} />
          </Fragment>)}
    </Screen>
  );
}
