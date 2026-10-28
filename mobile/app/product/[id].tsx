import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import AlertSheet from '@/components/AlertSheet';
import Flyer from '@/components/Flyer';
import ListPicker from '@/components/ListPicker';
import MarketBadge from '@/components/MarketBadge';
import ProductImage from '@/components/ProductImage';
import { Button, Card, Muted, Screen, useTheme } from '@/components/ui';
import { api, formatSize, GroupDetail, num, PriceAlert } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { useCatalog } from '@/lib/catalog';

/**
 * Ürün sayfası: seçili şubelerdeki her fiyat ayrı satır (web'deki gibi "BİM · Karlıdağ").
 * Bir satıra dokununca o ürün (marka) seçilir; seçilmezse listeye "Farketmez" (en ucuzu) eklenir.
 * Listeden gelindiyse (?listId=) ürün doğrudan o listeye eklenir. 🔔 ile fiyatı takip edilir (Alarmlar sekmesi).
 */
export default function ProductScreen() {
  const t = useTheme();
  const { id, listId } = useLocalSearchParams<{ id: string; listId?: string }>();
  const { user } = useAuth();
  const [selected, setSelected] = useState<number | null>(null); // seçili ürün = kilitli marka
  const [picking, setPicking] = useState(false);
  const [added, setAdded] = useState<string | null>(null); // hata mesajı
  const [flyer, setFlyer] = useState<string | null>(null); // eklenen listenin adı
  const [adding, setAdding] = useState(false);
  const { marketById, categoryIcon, categoryById } = useCatalog();
  const [group, setGroup] = useState<GroupDetail | null | undefined>(undefined);
  const [alert, setAlert] = useState<PriceAlert | null>(null);
  const [alertSheet, setAlertSheet] = useState(false);
  const [alertNote, setAlertNote] = useState<string | null>(null);

  useEffect(() => {
    api.productGroup(Number(id)).then(setGroup).catch(() => setGroup(null));
  }, [id]);
  useEffect(() => {
    if (!user) return;
    api.alerts().then(all => setAlert(all.find(a => a.group_id === Number(id)) || null)).catch(() => {});
  }, [id, user]);
  const openAlert = () => {
    if (!user) { router.push('/login'); return; }
    setAlertSheet(true);
  };

  const offers = useMemo(() => (group?.products ?? [])
    .filter(p => p.price != null)
    .flatMap(p => p.store_prices.length
      ? p.store_prices.map(sp => ({ key: `${p.id}-${sp.store_id}`, product: p, store: sp.store_name as string | null, price: num(sp.price) }))
      : [{ key: String(p.id), product: p, store: p.store_name, price: num(p.price) }])
    .sort((a, b) => a.price - b.price), [group]);

  const addTo = async (target: number) => {
    const updated = await api.addItem(target, Number(id), selected);
    setPicking(false);
    setAdded(null);
    setFlyer(updated.name); // onay kartı, ardından yönlendirme (afterFlyer)
  };
  const onAdd = async () => {
    if (!user) { router.push('/login'); return; }
    if (!listId) { setPicking(true); return; }
    setAdding(true);
    try { await addTo(Number(listId)); } catch (e) { setAdded((e as Error).message); } finally { setAdding(false); }
  };
  // Kemal: eklendikten sonra onay kartı ve ana sayfaya dönüş. Listenin içinden ürün eklerken listeye geri dönülür.
  const afterFlyer = () => {
    setFlyer(null);
    if (listId) router.dismissTo({ pathname: '/list/[id]', params: { id: listId } });
    else router.dismissTo('/');
  };
  const selectedProduct = group?.products.find(p => p.id === selected);

  if (group === undefined) return <Screen safeTop={false}><ActivityIndicator color={t.tint} style={{ marginTop: 40 }} /></Screen>;
  if (group === null) return <Screen safeTop={false}><Muted>Ürün bulunamadı.</Muted></Screen>;

  // Ürün kartı ve "Listeye ekle" sabit kalır; fiyat listesi aradaki kutunun içinde kayar (uzun listede düğme kaybolmasın)
  return (
    <SafeAreaView edges={['bottom']} style={{ flex: 1, backgroundColor: t.background, padding: 16, gap: 12 }}>
      <Stack.Screen options={{ title: group.name }} />
      <Card style={{ flexDirection: 'row', gap: 14, alignItems: 'center' }}>
        <ProductImage uri={group.image_url} icon={categoryIcon(group.category_id)} size={80} />
        <View style={{ flex: 1, gap: 4 }}>
          <Text style={{ color: t.text, fontSize: 18, fontWeight: '800' }}>{group.name}</Text>
          <Muted>{[formatSize(group.quantity, group.unit), categoryById(group.category_id)?.name].filter(Boolean).join(' · ')}</Muted>
        </View>
      </Card>

      <Card style={{ padding: 0, flex: 1, overflow: 'hidden' }}>
        <Text style={{ color: t.text, fontWeight: '700', padding: 14 }}>
          {new Set(offers.map(o => o.product.market_id)).size} markette bulundu
        </Text>
        <ScrollView>
        {offers.map((o, i) => (
          <Pressable key={o.key} onPress={() => setSelected(selected === o.product.id ? null : o.product.id)}
            style={{ flexDirection: 'row', alignItems: 'center', gap: 10, padding: 14, borderTopWidth: 1, borderTopColor: t.border,
              backgroundColor: selected === o.product.id ? t.tint + '22' : 'transparent' }}>
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
          </Pressable>
        ))}
        </ScrollView>
      </Card>

      <Muted>{selectedProduct ? `Seçili marka: ${selectedProduct.brand || selectedProduct.name} (tekrar dokunarak kaldırabilirsin)` : 'Marka seçmezsen listeye "Farketmez" eklenir, her zaman en ucuzu alınır.'}</Muted>
      <View style={{ flexDirection: 'row', gap: 8 }}>
        <View style={{ flex: 1 }}><Button title={listId ? 'Bu listeye ekle' : 'Listeye ekle'} onPress={onAdd} busy={adding} /></View>
        <Pressable onPress={openAlert} accessibilityLabel="Fiyatını takip et"
          style={{ paddingHorizontal: 14, borderRadius: 12, borderWidth: 1, justifyContent: 'center',
            borderColor: alert ? '#f59e0b' : t.border, backgroundColor: alert ? '#fef3c7' : t.card }}>
          <Text style={{ color: alert ? '#92400e' : t.text, fontWeight: '700' }}>{alert ? '🔔 Takipte' : '🔔 Takip et'}</Text>
          {alert?.brand && <Text style={{ color: '#92400e', fontSize: 10 }} numberOfLines={1}>{alert.brand}</Text>}
        </Pressable>
      </View>
      {alertNote && <Text style={{ color: t.tint, textAlign: 'center', fontWeight: '600' }}>{alertNote}</Text>}
      {added && <Text style={{ color: t.danger, textAlign: 'center', fontWeight: '600' }}>{added}</Text>}
      {flyer && <Flyer title="Listeye eklendi" subtitle={flyer} onDone={afterFlyer} />}
      <ListPicker visible={picking} onClose={() => setPicking(false)} onPick={addTo} />
      {alertSheet && (
        <AlertSheet visible onClose={() => setAlertSheet(false)} groupId={group.id} groupName={group.name}
          cheapest={offers[0]?.price ?? null} alert={alert}
          product={selectedProduct ? {
            id: selectedProduct.id,
            label: `${selectedProduct.brand || selectedProduct.name} · ${marketById(selectedProduct.market_id)?.name ?? ''}`,
            price: Math.min(...offers.filter(o => o.product.id === selectedProduct.id).map(o => o.price)),
          } : null}
          onChange={(a, message) => { setAlert(a); setAlertSheet(false); setAlertNote(message); }} />
      )}
    </SafeAreaView>
  );
}
