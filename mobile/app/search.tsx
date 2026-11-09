import { router, useLocalSearchParams } from 'expo-router';
import { Fragment, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, TextInput, View } from 'react-native';

import AdSlot from '@/components/AdSlot';
import { AD_EVERY, adsEnabled, interleaveAds } from '@/lib/ads';
import ProductRow from '@/components/ProductRow';
import Icon from '@/components/Icon';
import RecipeImage from '@/components/RecipeImage';
import { Card, Chip, EmptyState, Muted, Screen, Segmented, useTheme } from '@/components/ui';
import { api, COURSE_LABELS, CourseType, GroupSummary, num, RecipeSummary } from '@/lib/api';
import { courseGlyph } from '@/lib/icons';
import { useCatalog } from '@/lib/catalog';
import { Coords, getCoords } from '@/lib/location';

/** Ürün ve tarif araması (üstteki sekmeyle değişir). Ana sayfadaki arama çubuğu buraya açılır. */
export default function SearchScreen() {
  const t = useTheme();
  // listId: liste ekranındaki 'Ürün ekle'den gelindiyse ürün doğrudan o listeye eklenir
  const params = useLocalSearchParams<{ q?: string; listId?: string; mode?: string }>();
  const [mode, setMode] = useState<'urun' | 'tarif'>(params.mode === 'tarif' && !params.listId ? 'tarif' : 'urun');
  const [recipes, setRecipes] = useState<RecipeSummary[] | null>(null);
  const [course, setCourse] = useState<CourseType | null>(null);
  const [q, setQ] = useState(params.q ?? '');
  const [results, setResults] = useState<GroupSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { markets } = useCatalog();
  const [market, setMarket] = useState<number | null>(null); // yalnız bu marketin fiyatları
  // Konum varsa sunucu sonuçları seçili şubelerden en yakın olandan uzağa sıralar; yoksa kelime eşleşmesine ve ada göre
  const [at, setAt] = useState<Coords | null | undefined>(undefined); // undefined = konum sorgulanıyor
  useEffect(() => { getCoords().then(r => setAt(r.coords)); }, []);

  useEffect(() => {
    if (at === undefined) return;
    const term = q.trim();
    let cancelled = false;
    const timer = setTimeout(() => {
      if (mode === 'tarif') {
        if (!term) { setRecipes([]); return; }
        api.searchRecipes(term)
          .then(r => { if (!cancelled) { setRecipes(r); setError(null); } })
          .catch(e => { if (!cancelled) setError(e.message); });
        return;
      }
      if (!term) { setResults([]); return; }
      api.searchProducts(term, null, { at })
        .then(r => { if (!cancelled) { setResults(r); setError(null); } })
        .catch(e => { if (!cancelled) setError(e.message); });
    }, 300);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [q, mode, at]);

  const switchMode = (m: 'urun' | 'tarif') => { setMode(m); setError(null); setCourse(null); setRecipes(null); };
  const courses = Array.from(new Set((recipes ?? []).map(r => r.course_type)));
  const shownRecipes = (recipes ?? []).filter(r => course == null || r.course_type === course);

  const visible = (results ?? [])
    .map(g => ({ g, prices: market == null ? g.market_prices : g.market_prices.filter(m => m.market_id === market) }))
    .filter(x => x.prices.length > 0); // sıra sunucudan: en yakın marketten uzağa (fiyata göre değil)

  return (
    <Screen safeTop={false}>
      {!params.listId && (
        <Segmented value={mode} onChange={switchMode} options={[{ key: 'urun', label: 'Ürün' }, { key: 'tarif', label: 'Tarif' }]} />
      )}
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: t.card, borderRadius: 16, paddingHorizontal: 14,
        shadowColor: t.shadow, shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 3 }, elevation: 2 }}>
        <Icon name="search" size={20} color={t.textMuted} />
        <TextInput placeholder={mode === 'tarif' ? 'Tarif ara (örn. köfte, mercimek, tavuk)' : 'Ürün ara (örn. süt, ekmek, deterjan)'} placeholderTextColor={t.textMuted} value={q} onChangeText={setQ}
          autoFocus returnKeyType="search" autoCorrect={false}
          style={[{ flex: 1, color: t.text, fontSize: 16, paddingVertical: 14 }, { outlineStyle: 'none' } as object]} />
        {q !== '' && (
          <Pressable onPress={() => setQ('')} hitSlop={10} accessibilityLabel="Aramayı temizle"><Icon name="x-circle" size={20} color={t.textMuted} /></Pressable>
        )}
      </View>
      {mode === 'urun' && q.trim() !== '' && results && results.length > 0 && (
        <>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginHorizontal: -18 }} contentContainerStyle={{ paddingHorizontal: 18, gap: 8 }}>
            <Chip label="Tüm marketler" on={market == null} onPress={() => setMarket(null)} />
            {markets.map(m => <Chip key={m.id} label={m.name} on={market === m.id} onPress={() => setMarket(market === m.id ? null : m.id)} />)}
          </ScrollView>
          <Muted>{visible.length} ürün</Muted>
        </>
      )}
      {error && <Text style={{ color: t.danger }}>{error}</Text>}
      {mode === 'urun' && results === null && q.trim() !== '' && !error && <ActivityIndicator color={t.tint} style={{ marginTop: 24 }} />}
      {mode === 'urun' && q.trim() === '' && <EmptyState icon="search" title="Ne arıyorsunuz?" text="Ürün adını yazın, yakınınızdaki marketlerin fiyatlarını karşılaştıralım." />}
      {mode === 'urun' && q.trim() !== '' && results?.length === 0 && <EmptyState icon="search" title="Sonuç bulunamadı" text="Farklı bir yazım ya da daha kısa bir kelime deneyin." />}
      {/* Listeye ürün eklerken (listId) reklam gösterilmez: liste akışı temiz kalır */}
      {mode === 'urun' && interleaveAds(visible, AD_EVERY, !params.listId && adsEnabled()).map(r => r.kind === 'ad'
        ? <AdSlot key={r.key} placement="product-list" />
        : <Fragment key={r.item.g.id}>
            <ProductRow group={r.item.g} prices={r.item.prices} onPress={() => router.push({ pathname: '/product/[id]', params: params.listId ? { id: String(r.item.g.id), listId: params.listId } : { id: String(r.item.g.id) } })} />
          </Fragment>)}
      {mode === 'tarif' && (
        <>
          {q.trim() === '' && <EmptyState icon="search" title="Hangi yemeği arıyorsunuz?" text="Yemeğin adını ya da bir malzemeyi yazın; örneğin köfte, mercimek ya da tavuk." />}
          {q.trim() !== '' && recipes === null && !error && <ActivityIndicator color={t.tint} style={{ marginTop: 24 }} />}
          {q.trim() !== '' && recipes?.length === 0 && (
            <EmptyState icon="search" title="Tarif bulunamadı" text="Farklı bir yazım ya da daha kısa bir kelime deneyin."
              secondary={{ title: 'Menü planla', onPress: () => router.push('/meals') }} />
          )}
          {q.trim() !== '' && recipes && recipes.length > 0 && (
            <>
              {courses.length > 1 && (
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginHorizontal: -18 }} contentContainerStyle={{ paddingHorizontal: 18, gap: 8 }}>
                  <Chip label="Hepsi" on={course == null} onPress={() => setCourse(null)} />
                  {courses.map(c => <Chip key={c} label={COURSE_LABELS[c]} on={course === c} onPress={() => setCourse(course === c ? null : c)} />)}
                </ScrollView>
              )}
              <Muted>{shownRecipes.length} tarif</Muted>
              {shownRecipes.map(r => (
                <Pressable key={r.id} onPress={() => router.push({ pathname: '/recipe/[id]', params: { id: String(r.id) } })}
                  accessibilityRole="button" accessibilityLabel={r.name}>
                  <Card style={{ flexDirection: 'row', alignItems: 'center', gap: 14, minHeight: 72 }}>
                    <RecipeImage uri={r.image_url} icon={courseGlyph(r.course_type)} width={56} radius={12} iconSize={28} />
                    <View style={{ flex: 1, gap: 2 }}>
                      <Text style={{ color: t.text, fontWeight: '700', fontSize: 17 }} numberOfLines={2}>{r.name}</Text>
                      <Muted style={{ fontSize: 14 }}>
                        {r.course}{r.prep_minutes + r.cook_minutes > 0 ? ` · ${r.prep_minutes + r.cook_minutes} dk` : ''}
                      </Muted>
                    </View>
                  </Card>
                </Pressable>
              ))}
            </>
          )}
        </>
      )}
    </Screen>
  );
}
