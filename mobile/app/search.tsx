import { router, useLocalSearchParams } from 'expo-router';
import { Fragment, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, Text, TextInput, View } from 'react-native';

import AdSlot from '@/components/AdSlot';
import { AD_EVERY, adsEnabled, interleaveAds } from '@/lib/ads';
import ProductRow from '@/components/ProductRow';
import Icon from '@/components/Icon';
import { EmptyState, Muted, Screen, useTheme } from '@/components/ui';
import { api, GroupSummary } from '@/lib/api';

/** Ürün araması. Ana sayfadaki arama çubuğu buraya açılır. */
export default function SearchScreen() {
  const t = useTheme();
  // listId: liste ekranındaki 'Ürün ekle'den gelindiyse ürün doğrudan o listeye eklenir
  const params = useLocalSearchParams<{ q?: string; listId?: string }>();
  const [q, setQ] = useState(params.q ?? '');
  const [results, setResults] = useState<GroupSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <Screen safeTop={false}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: t.card, borderRadius: 16, paddingHorizontal: 14,
        shadowColor: t.shadow, shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 3 }, elevation: 2 }}>
        <Icon name="search" size={20} color={t.textMuted} />
        <TextInput placeholder="Ürün ara (örn. süt, ekmek, deterjan)" placeholderTextColor={t.textMuted} value={q} onChangeText={setQ}
          autoFocus returnKeyType="search" autoCorrect={false} style={{ flex: 1, color: t.text, fontSize: 16, paddingVertical: 14 }} />
        {q !== '' && (
          <Pressable onPress={() => setQ('')} hitSlop={10} accessibilityLabel="Aramayı temizle"><Icon name="x-circle" size={20} color={t.textMuted} /></Pressable>
        )}
      </View>
      {q.trim() !== '' && results && results.length > 0 && <Muted>{results.length} ürün</Muted>}
      {error && <Text style={{ color: t.danger }}>{error}</Text>}
      {results === null && q.trim() !== '' && !error && <ActivityIndicator color={t.tint} style={{ marginTop: 24 }} />}
      {q.trim() === '' && <EmptyState icon="search" title="Ne arıyorsun?" text="Ürün adını yaz, yakınındaki marketlerin fiyatlarını karşılaştıralım." />}
      {q.trim() !== '' && results?.length === 0 && <EmptyState icon="search" title="Sonuç bulunamadı" text="Farklı bir yazım ya da daha kısa bir kelime dene." />}
      {/* Listeye ürün eklerken (listId) reklam gösterilmez: liste akışı temiz kalır */}
      {interleaveAds(results ?? [], AD_EVERY, !params.listId && adsEnabled()).map(r => r.kind === 'ad'
        ? <AdSlot key={r.key} placement="product-list" />
        : <Fragment key={r.item.id}>
            <ProductRow group={r.item} onPress={() => router.push({ pathname: '/product/[id]', params: params.listId ? { id: String(r.item.id), listId: params.listId } : { id: String(r.item.id) } })} />
          </Fragment>)}
    </Screen>
  );
}
