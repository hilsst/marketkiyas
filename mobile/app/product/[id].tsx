import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';

import ListPicker from '@/components/ListPicker';
import MarketBadge from '@/components/MarketBadge';
import ProductImage from '@/components/ProductImage';
import { Button, Card, Muted, Screen, useTheme } from '@/components/ui';
import { api, formatSize, GroupDetail, num } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { useCatalog } from '@/lib/catalog';

/**
 * Ürün sayfası: seçili şubelerdeki her fiyat ayrı satır (web'deki gibi "BİM · Karlıdağ").
 * Bir satıra dokununca o ürün (marka) seçilir; seçilmezse listeye "Farketmez" (en ucuzu) eklenir.
 * Listeden gelindiyse (?listId=) ürün doğrudan o listeye eklenir. Fiyat alarmı 7. adımda.
 */
export default function ProductScreen() {
  const t = useTheme();
  const { id, listId } = useLocalSearchParams<{ id: string; listId?: string }>();
  const { user } = useAuth();
  const [selected, setSelected] = useState<number | null>(null); // seçili ürün = kilitli marka
  const [picking, setPicking] = useState(false);
  const [added, setAdded] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const { marketById, categoryIcon, categoryById } = useCatalog();
  const [group, setGroup] = useState<GroupDetail | null | undefined>(undefined);

  useEffect(() => {
    api.productGroup(Number(id)).then(setGroup).catch(() => setGroup(null));
  }, [id]);

  const offers = useMemo(() => (group?.products ?? [])
    .filter(p => p.price != null)
    .flatMap(p => p.store_prices.length
      ? p.store_prices.map(sp => ({ key: `${p.id}-${sp.store_id}`, product: p, store: sp.store_name as string | null, price: num(sp.price) }))
      : [{ key: String(p.id), product: p, store: p.store_name, price: num(p.price) }])
    .sort((a, b) => a.price - b.price), [group]);

  const addTo = async (target: number) => {
    await api.addItem(target, Number(id), selected);
    setPicking(false);
    setAdded('Listeye eklendi');
    if (listId) router.back();
  };
  const onAdd = async () => {
    if (!user) { router.push('/login'); return; }
    if (!listId) { setPicking(true); return; }
    setAdding(true);
    try { await addTo(Number(listId)); } catch (e) { setAdded((e as Error).message); } finally { setAdding(false); }
  };
  const selectedProduct = group?.products.find(p => p.id === selected);

  if (group === undefined) return <Screen safeTop={false}><ActivityIndicator color={t.tint} style={{ marginTop: 40 }} /></Screen>;
  if (group === null) return <Screen safeTop={false}><Muted>Ürün bulunamadı.</Muted></Screen>;

  return (
    <Screen safeTop={false}>
      <Stack.Screen options={{ title: group.name }} />
      <Card style={{ flexDirection: 'row', gap: 14, alignItems: 'center' }}>
        <ProductImage uri={group.image_url} icon={categoryIcon(group.category_id)} size={80} />
        <View style={{ flex: 1, gap: 4 }}>
          <Text style={{ color: t.text, fontSize: 18, fontWeight: '800' }}>{group.name}</Text>
          <Muted>{[formatSize(group.quantity, group.unit), categoryById(group.category_id)?.name].filter(Boolean).join(' · ')}</Muted>
        </View>
      </Card>

      <Card style={{ padding: 0 }}>
        <Text style={{ color: t.text, fontWeight: '700', padding: 14 }}>
          {new Set(offers.map(o => o.product.market_id)).size} markette bulundu
        </Text>
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
      </Card>

      <Muted>{selectedProduct ? `Seçili marka: ${selectedProduct.brand || selectedProduct.name} (tekrar dokunarak kaldırabilirsin)` : 'Marka seçmezsen listeye "Farketmez" eklenir, her zaman en ucuzu alınır.'}</Muted>
      <Button title={listId ? 'Bu listeye ekle' : 'Listeye ekle'} onPress={onAdd} busy={adding} />
      {added && <Text style={{ color: t.tint, textAlign: 'center', fontWeight: '600' }}>{added}</Text>}
      <ListPicker visible={picking} onClose={() => setPicking(false)} onPick={addTo} />
    </Screen>
  );
}
