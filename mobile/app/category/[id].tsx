import { router, Stack, useLocalSearchParams } from 'expo-router';
import { Fragment, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';

import AdSlot from '@/components/AdSlot';
import ProductRow from '@/components/ProductRow';
import { Muted, Screen, useTheme } from '@/components/ui';
import { api, GroupSummary } from '@/lib/api';
import { useCatalog } from '@/lib/catalog';

const PER_SECTION = 8; // "Tümü"de her alt kategoriden gösterilen ürün

/**
 * Kategori ekranı: üstte alt kategori şeridi (Tümü / Peynir / Yoğurt / Süt…). "Tümü"de her alt kategorinin en
 * temel ürünleri başlıkları altında; bir alt kategori seçilince yalnız onun ürünleri, her 4 üründe bir native reklam.
 */
export default function CategoryScreen() {
  const t = useTheme();
  const { id } = useLocalSearchParams<{ id: string }>();
  const categoryId = Number(id);
  const { categoryById, subcategoriesOf } = useCatalog();
  const subcats = useMemo(() => subcategoriesOf(categoryId), [subcategoriesOf, categoryId]);
  const [sub, setSub] = useState<number | null>(null);
  const [results, setResults] = useState<GroupSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = sub == null && subcats.length
      ? Promise.all(subcats.map(s => api.searchProducts('', categoryId, { sort: 'popular', subcategoryId: s.id, limit: PER_SECTION })))
          .then(parts => parts.flat())
      : api.searchProducts('', categoryId, { sort: 'popular', subcategoryId: sub, limit: 60 });
    load
      .then(r => { if (!cancelled) { setResults(r); setError(null); } })
      .catch(e => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, [categoryId, sub, subcats]);

  const open = (g: GroupSummary) => router.push({ pathname: '/product/[id]', params: { id: String(g.id) } });
  const sections = sub == null && subcats.length
    ? subcats.map(s => ({ sub: s, groups: (results ?? []).filter(g => g.subcategory_id === s.id) })).filter(s => s.groups.length)
    : null;

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
        {error && <Text style={{ color: t.danger }}>{error}</Text>}
        {results === null && !error && <ActivityIndicator color={t.tint} style={{ marginTop: 24 }} />}
        {results?.length === 0 && <Muted style={{ textAlign: 'center', marginTop: 24 }}>Bu bölümde ürün yok</Muted>}
        {sections
          ? sections.map(s => (
              <View key={s.sub.id} style={{ gap: 10 }}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <Text style={{ color: t.text, fontWeight: '700', fontSize: 16 }}>{s.sub.name}</Text>
                  <Text onPress={() => { setSub(s.sub.id); setResults(null); }} style={{ color: t.tint, fontWeight: '600' }}>Tümünü gör ›</Text>
                </View>
                {s.groups.map(g => <ProductRow key={g.id} group={g} onPress={() => open(g)} />)}
              </View>
            ))
          : results?.map((g, i) => (
              <Fragment key={g.id}>
                <ProductRow group={g} onPress={() => open(g)} />
                {i % 4 === 3 && <AdSlot placement="list" />}
              </Fragment>
            ))}
      </Screen>
    </>
  );
}
