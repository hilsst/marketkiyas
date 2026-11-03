import { router, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';

import { categoryGlyph } from '@/lib/icons';
import FoodIcon from '@/components/FoodIcon';
import AdSlot from '@/components/AdSlot';
import MarketBadge from '@/components/MarketBadge';
import ProductImage from '@/components/ProductImage';
import { cheapestOf } from '@/components/ProductRow';
import FamilyInviteCard from '@/components/FamilyInviteCard';
import Icon from '@/components/Icon';
import { Card, Muted, Screen, SectionHeader, Title, useTheme } from '@/components/ui';
import { AktuelItem, api, MyFamily, num, SavingsVault, Store } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { useCatalog } from '@/lib/catalog';

type ShowcaseItem = { id: number; name: string; image: string | null; categoryId: number | null;
  marketId: number | null; price: number | null; previous: number | null; badge: string | null };

/**
 * Ana sayfa, Kemal'in sırasıyla: arama, bu ayki tasarruf, hızlı erişim, kategoriler, fırsat ürünleri (yatay),
 * aktüel ürünler (yatay), yakındaki marketler. Tek reklam yeri: üst barın altı (ürün listelerinde ayrıca her 8 üründe bir).
 */
// Karşılama ekranı uygulama her açıldığında bir kez gösterilir
let welcomed = false;

export default function HomeScreen() {
  const t = useTheme();
  useEffect(() => {
    if (welcomed) return;
    welcomed = true;
    router.push('/welcome');
  }, []);
  const { user } = useAuth();
  const { categories, categoryIcon } = useCatalog();
  const [vault, setVault] = useState<SavingsVault | null>(null);
  const [stores, setStores] = useState<Store[] | null>(null);
  const [showcase, setShowcase] = useState<{ title: string; items: ShowcaseItem[] } | null>(null);

  const [family, setFamily] = useState<MyFamily | null>(null);
  const [aktuel, setAktuel] = useState<AktuelItem[]>([]);

  // Sekmeye her dönüşte: ailedeki biri alışverişi bitirmiş ya da davet gelmiş olabilir
  const refresh = useCallback(() => {
    if (!user) return;
    api.savings().then(setVault).catch(() => setVault(null));
    api.family().then(setFamily).catch(() => setFamily(null));
  }, [user]);
  useFocusEffect(refresh);

  useEffect(() => {
    if (!user) return;
    api.myStores().then(setStores).catch(() => setStores([]));
  }, [user]);

  // Satışta olan aktüellerden marketler sırayla (BİM, Şok, BİM...) en fazla 15; "Yakında"lar aktüel ekranında
  useEffect(() => {
    api.aktuel().then(d => {
      const byMarket = new Map<string, AktuelItem[]>();
      for (const i of d.items) if (!i.upcoming) byMarket.set(i.market_slug, [...(byMarket.get(i.market_slug) || []), i]);
      const queues = Array.from(byMarket.values());
      const mixed: AktuelItem[] = [];
      for (let k = 0; mixed.length < 15 && queues.some(q => k < q.length); k++) {
        for (const q of queues) if (k < q.length && mixed.length < 15) mixed.push(q[k]);
      }
      setAktuel(mixed);
    }).catch(() => setAktuel([]));
  }, []);

  // Fırsat varsa fırsatlar, yoksa en çok markette/markada bulunan temel ürünler
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const deals = await api.deals().catch(() => []);
      if (cancelled) return;
      if (deals.length) {
        setShowcase({ title: 'Bu haftanın fırsatları', items: deals.slice(0, 15).map(d => ({
          id: d.group_id, name: d.group_name, image: d.image_url, categoryId: d.category_id, marketId: d.market_id,
          price: num(d.price), previous: num(d.previous_price), badge: '%' + d.discount_percent })) });
        return;
      }
      const popular = await api.searchProducts('', null, { sort: 'popular', limit: 15 }).catch(() => []);
      if (cancelled) return;
      setShowcase({ title: 'Popüler ürünler', items: popular.map(g => {
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
      {/* Üst: selamlama + alarm zili (alarmlar artık buradan da açılır) */}
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <View>
          <Muted style={{ fontSize: 14 }}>{user ? 'Merhaba' : 'Hoş geldin'}</Muted>
          <Title>{user?.full_name?.split(' ')[0] || 'Ucuzu'}</Title>
        </View>
        <Pressable onPress={() => router.push('/alerts')} accessibilityRole="button" accessibilityLabel="Fiyat alarmları"
          style={{ width: 46, height: 46, borderRadius: 16, backgroundColor: t.card, alignItems: 'center', justifyContent: 'center',
            shadowColor: t.shadow, shadowOpacity: 0.07, shadowRadius: 10, shadowOffset: { width: 0, height: 3 }, elevation: 2 }}>
          <Icon name="bell" size={22} />
        </Pressable>
      </View>

      {/* 1) Arama: dokununca arama ekranı açılır */}
      <Pressable onPress={() => router.push('/search')} accessibilityRole="search"
        style={{ borderRadius: 16, backgroundColor: t.card, padding: 15, flexDirection: 'row', alignItems: 'center', gap: 10,
          shadowColor: t.shadow, shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 3 }, elevation: 2 }}>
        <Icon name="search" size={20} color={t.textMuted} />
        <Muted style={{ fontSize: 15 }}>Ürün ara (örn. süt, ekmek, deterjan)</Muted>
      </Pressable>

      <AdSlot placement="home-top" />

      {user && family?.invites.map(inv => <FamilyInviteCard key={inv.id} invite={inv} onDone={setFamily} />)}

      {/* 2) Bu ayki tasarruf */}
      {user ? (
        <Pressable onPress={() => router.push('/profile')} style={{ backgroundColor: t.tint, borderRadius: 22, padding: 20, gap: 4 }}>
          <Text style={{ color: '#fff', fontSize: 12, fontWeight: '700', opacity: 0.9, letterSpacing: 0.5 }}>{monthName.toLocaleUpperCase('tr-TR')} AYI TASARRUFUN</Text>
          <Text style={{ color: '#fff', fontSize: 40, fontWeight: '800', letterSpacing: -1 }}>{monthSaved.toFixed(2)} ₺</Text>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
            <Icon name="trending-up" size={16} color="#fff" />
            <Text style={{ color: '#fff', fontSize: 13, opacity: 0.9 }}>
              Toplam {num(vault?.total_saved).toFixed(2)} ₺ · {monthSaved > 0 ? 'Böyle devam!' : 'Bir liste oluştur, Fırsatçı planla başla'}
            </Text>
          </View>
          {family?.family && (
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 6 }}>
              <Icon name="users" size={16} color="#fff" />
              <Text style={{ color: '#fff', fontSize: 14, fontWeight: '700' }}>Ailenin bu ayki tasarrufu: {num(family.family.month_saved).toFixed(2)} ₺</Text>
            </View>
          )}
        </Pressable>
      ) : (
        <Pressable onPress={() => router.push('/login')}>
          <Card style={{ gap: 4 }}>
            <Text style={{ color: t.text, fontWeight: '700' }}>Tasarrufunu takip et</Text>
            <Muted>Giriş yap, her ay ne kadar kazandığını burada gör.</Muted>
          </Card>
        </Pressable>
      )}

      {/* Yemek planı ve indirimden menü: iki ana giriş */}
      <Pressable onPress={() => router.push('/meals')} accessibilityRole="button">
        <Card style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
          <View style={{ width: 46, height: 46, borderRadius: 15, backgroundColor: t.tintSoft, alignItems: 'center', justifyContent: 'center' }}>
            <Icon name="coffee" size={24} color={t.tint} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={{ color: t.text, fontWeight: '800', fontSize: 16 }}>Yemek Planı</Text>
            <Muted>Menü kur, maliyeti gör, listene aktar.</Muted>
          </View>
          <Icon name="chevron-right" size={20} color={t.textMuted} />
        </Card>
      </Pressable>
      <Pressable onPress={() => router.push('/meals/deals')} accessibilityRole="button">
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14, borderRadius: 20, padding: 16, backgroundColor: t.accentSoft }}>
          <View style={{ width: 46, height: 46, borderRadius: 15, backgroundColor: t.accent, alignItems: 'center', justifyContent: 'center' }}>
            <Icon name="tag" size={24} color="#fff" />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={{ color: t.text, fontWeight: '800', fontSize: 16 }}>İndirimden menü</Text>
            <Text style={{ color: t.accentText, fontSize: 13 }}>Bu hafta indirimdeki malzemelerle menü kur.</Text>
          </View>
          <Icon name="chevron-right" size={20} color={t.accentText} />
        </View>
      </Pressable>

      {/* 4) Kategoriler */}
      <View style={{ gap: 12 }}>
        <SectionHeader title="Kategoriler" />
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
          {categories.map(c => (
            <Pressable key={c.id} onPress={() => router.push({ pathname: '/category/[id]', params: { id: String(c.id) } })}
              style={{ width: '23%', flexGrow: 1 }}>
              <Card style={{ alignItems: 'center', paddingVertical: 12, paddingHorizontal: 4, gap: 6 }}>
                <FoodIcon name={categoryGlyph(c.slug)} size={28} />
                <Text style={{ color: t.text, fontSize: 11, textAlign: 'center' }} numberOfLines={2}>{c.name}</Text>
              </Card>
            </Pressable>
          ))}
        </View>
      </View>

      {/* 5) Fırsat / popüler ürünler (yatay) */}
      {showcase && showcase.items.length > 0 && (
        <View style={{ gap: 10 }}>
          <SectionHeader title={showcase.title} action="Tümü" onAction={() => router.push('/deals')} />
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginHorizontal: -16 }} contentContainerStyle={{ paddingHorizontal: 16, gap: 10 }}>
            {showcase.items.map(it => (
              <Pressable key={it.id} onPress={() => router.push({ pathname: '/product/[id]', params: { id: String(it.id) } })}>
                <Card style={{ width: 140, gap: 6, padding: 12 }}>
                  {it.badge && (
                    <Text style={{ position: 'absolute', top: 8, right: 8, zIndex: 1, backgroundColor: t.accent, color: '#fff',
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

      {/* 6) Marketlerin aktüelleri (yatay) */}
      {aktuel.length > 0 && (
        <View style={{ gap: 10 }}>
          <SectionHeader title="Aktüel Ürünler" action="Tümü" onAction={() => router.push('/aktuel')} />
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginHorizontal: -16 }} contentContainerStyle={{ paddingHorizontal: 16, gap: 10 }}>
            {aktuel.map(it => (
              <Pressable key={it.id} onPress={() => router.push({ pathname: '/aktuel', params: { market: it.market_slug } })}>
                <Card style={{ width: 140, gap: 6, padding: 12 }}>
                  <View style={{ alignItems: 'center' }}><ProductImage uri={it.image_url} icon="newspaper-variant-outline" size={70} /></View>
                  <Text style={{ color: t.text, fontSize: 12, fontWeight: '600', minHeight: 32 }} numberOfLines={2}>{it.title}</Text>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                    <MarketBadge slug={it.market_slug} size={18} />
                    <Text style={{ color: t.tint, fontWeight: '800' }}>{num(it.price).toFixed(2)} ₺</Text>
                  </View>
                  <Text style={{ color: t.textMuted, fontSize: 10 }} numberOfLines={1}>{it.period_label}</Text>
                </Card>
              </Pressable>
            ))}
          </ScrollView>
        </View>
      )}

      {/* 7) Yakındaki marketler */}
      <View style={{ gap: 10 }}>
        <SectionHeader title="Yakınındaki Marketler" action="Düzenle" onAction={() => router.push('/stores')} />
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
