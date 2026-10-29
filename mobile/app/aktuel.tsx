import { router, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Image, Linking, Modal, Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import AdSlot from '@/components/AdSlot';
import MarketBadge from '@/components/MarketBadge';
import ProductImage from '@/components/ProductImage';
import { Button, Card, Muted, useTheme } from '@/components/ui';
import { AktuelItem, AktuelResponse, api, num } from '@/lib/api';

// Bir bölümde ilk bu kadar ürün görünür, gerisi "Tümünü göster" ile açılır (yüzlerce ürün tek seferde çizilmesin)
const PREVIEW = 6;

type Section = { key: string; slug: string; label: string; note: string; upcoming: boolean; items: AktuelItem[] };

const tl = (v: string | number | null) => `${num(v).toFixed(2)} ₺`;

function sectionNote(item: AktuelItem): string {
  if (item.upcoming) return 'Yakında mağazalarda';
  if (item.ends_on) return 'Bu tarihler arasında indirimli';
  if (item.starts_on) return 'Bu tarihten beri satışta · stoklarla sınırlı';
  return 'Bu haftanın fırsatları';
}

/** Aktüel: BİM, Şok... broşür ürünleri; market süzgeci, tarihe göre bölümler, diğer marketler için site bağlantısı */
export default function AktuelScreen() {
  const t = useTheme();
  const params = useLocalSearchParams<{ market?: string }>();
  const [data, setData] = useState<AktuelResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [market, setMarket] = useState<string | null>(params.market || null); // null = tüm marketler
  const [open, setOpen] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<AktuelItem | null>(null);
  const [failedImage, setFailedImage] = useState<number | null>(null); // büyük görsel açılmazsa boş alan kalmasın

  const load = useCallback(() => api.aktuel()
    .then(d => { setData(d); setError(null); })
    .catch(e => setError((e as Error).message)), []);
  useEffect(() => { load(); }, [load]);

  const nameOf = useCallback((slug: string) => data?.sources.find(s => s.slug === slug)?.name || slug, [data]);
  const withItems = (data?.sources || []).filter(s => s.item_count > 0);
  const linkOnly = (data?.sources || []).filter(s => !s.automatic);

  const sections = useMemo(() => {
    const bySection = new Map<string, Section>();
    for (const item of data?.items || []) {
      if (market && item.market_slug !== market) continue;
      const key = `${item.market_slug}:${item.period_key}`;
      let section = bySection.get(key);
      if (!section) {
        section = { key, slug: item.market_slug, label: item.period_label, note: sectionNote(item), upcoming: item.upcoming, items: [] };
        bySection.set(key, section);
      }
      section.items.push(item);
    }
    return Array.from(bySection.values());
  }, [data, market]);

  const chip = (key: string, active: boolean, onPress: () => void, label: React.ReactNode) => (
    <Pressable key={key} onPress={onPress} style={{ flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 7,
      borderRadius: 999, borderWidth: 1, borderColor: active ? t.tint : t.border, backgroundColor: active ? t.tint : t.card }}>
      {label}
    </Pressable>
  );
  const chipText = (active: boolean, text: string) => <Text style={{ color: active ? '#fff' : t.text, fontSize: 13, fontWeight: '600' }}>{text}</Text>;

  return (
    <SafeAreaView edges={[]} style={{ flex: 1, backgroundColor: t.background }}>
      <ScrollView refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load().finally(() => setRefreshing(false)); }} />}>
        <View style={{ padding: 16, gap: 16 }}>
          <Muted>Marketlerin broşürlerindeki aktüel ürünler. Aktüel ürünler stoklarla sınırlıdır; mağazada fiyat farklı olabilir.</Muted>

          {withItems.length > 1 && (
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginHorizontal: -16 }} contentContainerStyle={{ paddingHorizontal: 16, gap: 8 }}>
              {chip('all', market == null, () => setMarket(null), chipText(market == null, 'Tüm marketler'))}
              {withItems.map(s => chip(s.slug, market === s.slug, () => setMarket(s.slug),
                <><MarketBadge slug={s.slug} name={s.name} size={18} />{chipText(market === s.slug, `${s.name} (${s.item_count})`)}</>))}
            </ScrollView>
          )}

          {error && <Card><Text style={{ color: t.danger }}>Aktüeller yüklenemedi: {error}</Text></Card>}
          {data === null && !error && <ActivityIndicator color={t.tint} style={{ marginTop: 24 }} />}
          {data && sections.length === 0 && (
            <Card style={{ alignItems: 'center', gap: 6, padding: 24 }}>
              <Text style={{ fontSize: 30 }}>📰</Text>
              <Text style={{ color: t.text }}>Henüz aktüel ürün yok</Text>
              <Muted style={{ textAlign: 'center' }}>Broşürler günde iki kez güncellenir.</Muted>
            </Card>
          )}

          {sections.map((section, index) => {
            const expanded = open.has(section.key);
            const shown = expanded ? section.items : section.items.slice(0, PREVIEW);
            return (
              <View key={section.key} style={{ gap: 10 }}>
                {index === 1 && <AdSlot placement="list" />}
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                  <MarketBadge slug={section.slug} name={nameOf(section.slug)} size={30} />
                  <View style={{ flex: 1 }}>
                    <Text style={{ color: t.text, fontWeight: '800', fontSize: 16 }}>{nameOf(section.slug)} · {section.label}</Text>
                    <Text style={{ color: section.upcoming ? '#7c3aed' : t.textMuted, fontSize: 12, fontWeight: section.upcoming ? '700' : '400' }}>
                      {section.note} · {section.items.length} ürün
                    </Text>
                  </View>
                </View>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10 }}>
                  {shown.map(item => (
                    <Pressable key={item.id} style={{ width: '48%', flexGrow: 1 }} onPress={() => setSelected(item)}>
                      <Card style={{ gap: 6, padding: 12, flex: 1 }}>
                        {item.old_price && (
                          <Text style={{ position: 'absolute', top: 8, right: 8, zIndex: 1, backgroundColor: '#ef4444', color: '#fff',
                            fontSize: 11, fontWeight: '800', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, overflow: 'hidden' }}>
                            %{Math.round((1 - num(item.price) / num(item.old_price)) * 100)}
                          </Text>
                        )}
                        <View style={{ alignItems: 'center' }}><ProductImage uri={item.image_url} icon="📰" size={96} /></View>
                        {item.brand && <Text style={{ color: t.textMuted, fontSize: 11, fontWeight: '700' }} numberOfLines={1}>{item.brand}</Text>}
                        <Text style={{ color: t.text, fontSize: 13, fontWeight: '600', minHeight: 34 }} numberOfLines={2}>{item.title}</Text>
                        {item.quantity_text && <Text style={{ color: t.textMuted, fontSize: 11 }}>{item.quantity_text}</Text>}
                        <View style={{ marginTop: 'auto', gap: 2 }}>
                          {item.old_price && <Text style={{ color: t.textMuted, fontSize: 11, textDecorationLine: 'line-through' }}>{tl(item.old_price)}</Text>}
                          <Text style={{ color: t.tint, fontWeight: '800', fontSize: 15 }}>{tl(item.price)}</Text>
                        </View>
                      </Card>
                    </Pressable>
                  ))}
                </View>
                {section.items.length > PREVIEW && (
                  <Pressable onPress={() => setOpen(prev => {
                    const next = new Set(prev);
                    if (expanded) next.delete(section.key); else next.add(section.key);
                    return next;
                  })}>
                    <Text style={{ color: t.tint, fontWeight: '700', textAlign: 'center', paddingVertical: 4 }}>
                      {expanded ? 'Daha az göster' : `Tümünü göster (${section.items.length})`}
                    </Text>
                  </Pressable>
                )}
              </View>
            );
          })}

          {linkOnly.length > 0 && (
            <Card style={{ gap: 10 }}>
              <Text style={{ color: t.text, fontWeight: '800' }}>Diğer marketlerin aktüelleri</Text>
              <Muted>Bu marketlerin broşürlerini henüz uygulamaya alamıyoruz; marketin kendi sitesinde açılır.</Muted>
              {linkOnly.map(s => (
                <Pressable key={s.slug} onPress={() => Linking.openURL(s.url)}
                  style={{ flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 6 }}>
                  <MarketBadge slug={s.slug} name={s.name} size={28} />
                  <Text style={{ color: t.text, fontWeight: '600', flex: 1 }}>{s.name}</Text>
                  <Text style={{ color: t.tint, fontWeight: '600' }}>Sitede aç ›</Text>
                </Pressable>
              ))}
            </Card>
          )}
        </View>
      </ScrollView>

      <Modal visible={selected != null} transparent animationType="slide" onRequestClose={() => setSelected(null)}>
        <Pressable onPress={() => setSelected(null)} style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.35)', justifyContent: 'flex-end' }}>
          {selected && (
            <Pressable onPress={() => undefined} style={{ backgroundColor: t.card, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, gap: 10, maxHeight: '85%' }}>
              <ScrollView contentContainerStyle={{ gap: 10 }}>
                {selected.image_url && failedImage !== selected.id && (
                  <Image source={{ uri: selected.image_url }} resizeMode="contain" onError={() => setFailedImage(selected.id)}
                    style={{ width: '100%', aspectRatio: 1.16, borderRadius: 12, backgroundColor: '#fff' }} />
                )}
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <MarketBadge slug={selected.market_slug} name={nameOf(selected.market_slug)} size={22} />
                  <Muted>{nameOf(selected.market_slug)} · {selected.period_label}</Muted>
                </View>
                {selected.brand && <Text style={{ color: t.textMuted, fontWeight: '700' }}>{selected.brand}</Text>}
                <Text style={{ color: t.text, fontSize: 18, fontWeight: '800' }}>{selected.title}</Text>
                {selected.quantity_text && <Muted>{selected.quantity_text}</Muted>}
                {selected.details && <Text style={{ color: t.text }}>{selected.details.split('\n').map(l => `• ${l}`).join('\n')}</Text>}
                <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 10 }}>
                  <Text style={{ color: t.tint, fontSize: 24, fontWeight: '900' }}>{tl(selected.price)}</Text>
                  {selected.old_price && <Text style={{ color: t.textMuted, textDecorationLine: 'line-through' }}>{tl(selected.old_price)}</Text>}
                </View>
                <Muted>{sectionNote(selected)}</Muted>
              </ScrollView>
              {selected.source_url && <Button title="Marketin sitesinde gör" onPress={() => Linking.openURL(selected.source_url!)} />}
              <Button title="Diğer marketlerde ara" kind="secondary"
                onPress={() => { const q = [selected.brand, selected.title].filter(Boolean).join(' '); setSelected(null); router.push({ pathname: '/search', params: { q } }); }} />
            </Pressable>
          )}
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}
