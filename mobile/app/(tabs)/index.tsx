import { router } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';

import AdSlot from '@/components/AdSlot';
import MarketBadge from '@/components/MarketBadge';
import ProductImage from '@/components/ProductImage';
import { cheapestOf } from '@/components/ProductRow';
import { Card, Muted, Screen, Title, useTheme } from '@/components/ui';
import { api, num, SavingsVault, Store } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { useCatalog } from '@/lib/catalog';

type ShowcaseItem = { id: number; name: string; image: string | null; categoryId: number | null;
  marketId: number | null; price: number | null; previous: number | null; badge: string | null };

const QUICK = [
  { href: '/lists', icon: '📋', label: 'Listelerim' },
  { href: '/deals', icon: '🏷️', label: 'Fırsatlar' },
  { href: '/alerts', icon: '🔔', label: 'Alarmlar' },
  { href: '/stores', icon: '📍', label: 'Yakınımdakiler' },
] as const;

/**
 * Ana sayfa, Kemal'in sırasıyla: arama, bu ayki tasarruf, hızlı erişim, kategoriler, fırsat ürünleri (yatay),
 * yakındaki marketler. Reklam yerleri: üst barın altı ve kategorilerin bitimi.
 */
export default function HomeScreen() {
  const t = useTheme();
  const { user } = useAuth();
  const { categories, categoryIcon } = useCatalog();
  const [vault, setVault] = useState<SavingsVault | null>(null);
  const [stores, setStores] = useState<Store[] | null>(null);
  const [showcase, setShowcase] = useState<{ title: string; items: ShowcaseItem[] } | null>(null);

  useEffect(() => {
    if (!user) return;
    api.savings().then(setVault).catch(() => setVault(null));
    api.myStores().then(setStores).catch(() => setStores([]));
  }, [user]);

  // Fırsat varsa fırsatlar, yoksa en çok markette/markada bulunan temel ürünler
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const deals = await api.deals().catch(() => []);
      if (cancelled) return;
      if (deals.length) {
        setShowcase({ title: '🏷️ Fırsat Ürünleri', items: deals.slice(0, 15).map(d => ({
          id: d.group_id, name: d.group_name, image: d.image_url, categoryId: d.category_id, marketId: d.market_id,
          price: num(d.price), previous: num(d.previous_price), badge: '%' + d.discount_percent })) });
        return;
      }
      const popular = await api.searchProducts('', null, { sort: 'popular', limit: 15 }).catch(() => []);
      if (cancelled) return;
      setShowcase({ title: '⭐ Popüler Ürünler', items: popular.map(g => {
        const c = cheapestOf(g.market_prices);
        return { id: g.id, name: g.name, image: g.image_url, categoryId: g.category_id, marketId: c?.market_id ?? null,
          price: c ? num(c.min_price) : null, previous: null, badge: null };
      }) });
    })();
    return () => { cancelled = true; };
  }, [user]);

  const monthSaved = useMemo(() => {
    const now = new Date();
    return (user && vault?.records ? vault.records : [])
      .filter(r => { const d = new Date(r.created_at); return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth(); })
      .reduce((sum, r) => sum + num(r.saved_amount), 0);
  }, [vault, user]);
  const monthName = new Date().toLocaleDateString('tr-TR', { month: 'long' });

  return (
    <Screen>
      <Title>🛒 Ucuzu</Title>

      {/* 1) Arama: dokununca arama ekranı açılır */}
      <Pressable onPress={() => router.push('/search')} accessibilityRole="search"
        style={{ borderRadius: 12, borderWidth: 1, borderColor: t.border, backgroundColor: t.card, padding: 14 }}>
        <Muted style={{ fontSize: 16 }}>🔍  Ürün ara (örn. süt, ekmek, deterjan)</Muted>
      </Pressable>

      <AdSlot placement="home-top" />

      {/* 2) Bu ayki tasarruf */}
      {user ? (
        <Pressable onPress={() => router.push('/profile')} style={{ backgroundColor: t.tint, borderRadius: 18, padding: 18, gap: 4 }}>
          <Text style={{ color: '#fff', fontSize: 12, fontWeight: '700', opacity: 0.9 }}>BU AYKİ TASARRUFUN · {monthName.toLocaleUpperCase('tr-TR')}</Text>
          <Text style={{ color: '#fff', fontSize: 38, fontWeight: '900' }}>{monthSaved.toFixed(2)} ₺</Text>
          <Text style={{ color: '#fff', fontSize: 12, opacity: 0.85 }}>
            Toplam: {num(vault?.total_saved).toFixed(2)} ₺ · {monthSaved > 0 ? 'Böyle devam!' : 'Bir liste oluştur, Fırsatçı planla başla'}
          </Text>
        </Pressable>
      ) : (
        <Pressable onPress={() => router.push('/login')}>
          <Card style={{ gap: 4 }}>
            <Text style={{ color: t.text, fontWeight: '700' }}>Tasarrufunu takip et</Text>
            <Muted>Giriş yap, her ay ne kadar kazandığını burada gör.</Muted>
          </Card>
        </Pressable>
      )}

      {/* 3) Hızlı erişim */}
      <View style={{ flexDirection: 'row', gap: 8 }}>
        {QUICK.map(q => (
          <Pressable key={q.href} onPress={() => router.push(q.href)} style={{ flex: 1 }}>
            <Card style={{ alignItems: 'center', paddingVertical: 12, paddingHorizontal: 4, gap: 6 }}>
              <Text style={{ fontSize: 24 }}>{q.icon}</Text>
              <Text style={{ color: t.text, fontSize: 11, fontWeight: '600', textAlign: 'center' }} numberOfLines={1}>{q.label}</Text>
            </Card>
          </Pressable>
        ))}
      </View>

      {/* 4) Kategoriler */}
      <View style={{ gap: 10 }}>
        <Text style={{ color: t.text, fontWeight: '800', fontSize: 17 }}>Kategoriler</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
          {categories.map(c => (
            <Pressable key={c.id} onPress={() => router.push({ pathname: '/category/[id]', params: { id: String(c.id) } })}
              style={{ width: '23%', flexGrow: 1 }}>
              <Card style={{ alignItems: 'center', paddingVertical: 12, paddingHorizontal: 4, gap: 6 }}>
                <Text style={{ fontSize: 26 }}>{c.icon || '🛒'}</Text>
                <Text style={{ color: t.text, fontSize: 11, textAlign: 'center' }} numberOfLines={2}>{c.name}</Text>
              </Card>
            </Pressable>
          ))}
        </View>
      </View>

      <AdSlot placement="home-categories" />

      {/* 5) Fırsat / popüler ürünler (yatay) */}
      {showcase && showcase.items.length > 0 && (
        <View style={{ gap: 10 }}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <Text style={{ color: t.text, fontWeight: '800', fontSize: 17 }}>{showcase.title}</Text>
            <Text onPress={() => router.push('/deals')} style={{ color: t.tint, fontWeight: '600' }}>Tümü ›</Text>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginHorizontal: -16 }} contentContainerStyle={{ paddingHorizontal: 16, gap: 10 }}>
            {showcase.items.map(it => (
              <Pressable key={it.id} onPress={() => router.push({ pathname: '/product/[id]', params: { id: String(it.id) } })}>
                <Card style={{ width: 140, gap: 6, padding: 12 }}>
                  {it.badge && (
                    <Text style={{ position: 'absolute', top: 8, right: 8, zIndex: 1, backgroundColor: '#f97316', color: '#fff',
                      fontSize: 10, fontWeight: '800', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, overflow: 'hidden' }}>{it.badge}</Text>
                  )}
                  <View style={{ alignItems: 'center' }}><ProductImage uri={it.image} icon={categoryIcon(it.categoryId)} size={70} /></View>
                  <Text style={{ color: t.text, fontSize: 12, fontWeight: '600', minHeight: 32 }} numberOfLines={2}>{it.name}</Text>
                  {it.price != null && (
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                      {it.marketId != null && <MarketBadge id={it.marketId} size={18} />}
                      <Text style={{ color: t.tint, fontWeight: '800' }}>{it.price.toFixed(2)} ₺</Text>
                    </View>
                  )}
                  {it.previous != null && it.previous > (it.price ?? 0) && (
                    <Text style={{ color: t.textMuted, fontSize: 11, textDecorationLine: 'line-through' }}>{it.previous.toFixed(2)} ₺</Text>
                  )}
                </Card>
              </Pressable>
            ))}
          </ScrollView>
        </View>
      )}

      {/* 6) Yakındaki marketler */}
      <View style={{ gap: 10 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <Text style={{ color: t.text, fontWeight: '800', fontSize: 17 }}>📍 Yakınındaki Marketler</Text>
          <Text onPress={() => router.push('/stores')} style={{ color: t.tint, fontWeight: '600' }}>Düzenle ›</Text>
        </View>
        {user && stores && stores.length > 0 ? (
          <Card style={{ padding: 0 }}>
            {stores.map((s, i) => (
              <View key={s.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, borderTopWidth: i ? 1 : 0, borderTopColor: t.border }}>
                <MarketBadge id={s.market_id} size={30} />
                <View style={{ flex: 1 }}>
                  <Text style={{ color: t.text, fontWeight: '600' }} numberOfLines={1}>{s.name}</Text>
                  <Muted>{s.market_name}{s.distance_km != null ? ` · ${s.distance_km.toFixed(1)} km` : ''}</Muted>
                </View>
              </View>
            ))}
          </Card>
        ) : (
          <Pressable onPress={() => router.push(user ? '/stores' : '/login')}>
            <Card><Muted>Fiyatların senin şubelerine göre hesaplanması için yakınındaki marketleri seç ›</Muted></Card>
          </Pressable>
        )}
      </View>
    </Screen>
  );
}
