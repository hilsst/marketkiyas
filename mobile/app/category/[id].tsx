import { router, Stack, useLocalSearchParams } from 'expo-router';
import { Fragment, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';

import AdSlot from '@/components/AdSlot';
import ProductRow from '@/components/ProductRow';
import { Input, Muted, Screen, useTheme } from '@/components/ui';
import { api, GroupSummary } from '@/lib/api';
import { interleaveAds } from '@/lib/ads';
import { useCatalog } from '@/lib/catalog';

/**
 * Kategori ekranı (sade): üstte alt kategori şeridi ve arama kutusu, altında tek düz ürün listesi
 * (popülerden). Tek istek atar; her 8 üründe bir reklam yeri. Alt kategori başlıkları ve "Tümünü gör"
 * bölümleri kaldırıldı: bu alanda arama + barkod + ürün sayfası yeter (Faz Planı v2).
 */
export default function CategoryScreen() {
  const t = useTheme();
  const { id } = useLocalSearchParams<{ id: string }>();
  const categoryId = Number(id);
  const { categoryById, subcategoriesOf } = useCatalog();
  const subcats = useMemo(() => subcategoriesOf(categoryId), [subcategoriesOf, categoryId]);
  const [sub, setSub] = useState<number | null>(null);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<GroupSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    // Yazarken her tuşta istek atılmasın
    const timer = setTimeout(() => {
      api.searchProducts(query.trim(), categoryId, { sort: query.trim() ? 'name' : 'popular', subcategoryId: sub, limit: 60 })
        .then(r => { if (!cancelled) { setResults(r); setError(null); } })
        .catch(e => { if (!cancelled) setError(e.message); });
    }, query ? 300 : 0);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [categoryId, sub, query]);

  const open = (g: GroupSummary) => router.push({ pathname: '/product/[id]', params: { id: String(g.id) } });
  const rows = useMemo(() => interleaveAds(results ?? []), [results]);

  return (
    <>
      <Stack.Screen options={{ title: categoryById(categoryId)?.name ?? 'Kategori' }} />
      {subcats.length > 0 && (
        <View style={{ backgroundColor: t.background, borderBottomWidth: 1, borderBottomColor: t.border }}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ padding: 12, gap: 8 }}>
            {[{ id: null as number | null, name: 'Tümü' }, ...subcats.map(s => ({ id: s.id as number | null, name: s.name }))].map(c => {
              const on = sub === c.id;
              return (
                <Pressable key={c.id ?? 'all'} onPress={() => { setSub(c.id); setResults(null); }}
                  style={{ paddingHorizontal: 14, paddingVertical: 8, borderRadius: 12, borderWidth: 1,
                    backgroundColor: on ? t.tint : t.card, borderColor: on ? t.tint : t.border }}>
                  <Text style={{ color: on ? '#fff' : t.text, fontWeight: on ? '700' : '500' }}>{c.name}</Text>
                </Pressable>
              );
            })}
          </ScrollView>
        </View>
      )}
      <Screen safeTop={false}>
        <Input placeholder="Bu kategoride ara" value={query} onChangeText={v => { setQuery(v); setResults(null); }}
          autoCorrect={false} returnKeyType="search" />
        {error && <Text style={{ color: t.danger }}>{error}</Text>}
        {results === null && !error && <ActivityIndicator color={t.tint} style={{ marginTop: 24 }} />}
        {results?.length === 0 && <Muted style={{ textAlign: 'center', marginTop: 24 }}>Ürün bulunamadı</Muted>}
        {rows.map(r => r.kind === 'ad'
          ? <AdSlot key={r.key} placement="product-list" />
          : <Fragment key={r.item.id}><ProductRow group={r.item} onPress={() => open(r.item)} /></Fragment>)}
      </Screen>
    </>
  );
}
