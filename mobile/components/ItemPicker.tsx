import { ReactNode, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Modal, Pressable, ScrollView, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import Icon from '@/components/Icon';
import MarketBadge from '@/components/MarketBadge';
import { Muted, useTheme } from '@/components/ui';
import { api, GroupDetail, ItemPatch, ListItem, num } from '@/lib/api';
import { useCatalog } from '@/lib/catalog';
import { formatTL } from '@/lib/format';

interface Offer { key: string; productId: number; brand: string | null; name: string; marketId: number; store: string | null; price: number }

/**
 * Listede bir ürüne dokununca açılan seçim penceresi: "Farketmez (en ucuzu)", bir marka (her markette en
 * ucuzu) ya da belirli bir market/ürün. Seçim Kombinasyon, Tek Market ve Yakın Market planlarında korunur;
 * Fırsatçı yok sayar.
 */
export default function ItemPicker({ item, onClose, onPick }: {
  item: ListItem | null; onClose: () => void; onPick: (patch: ItemPatch) => void;
}) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const { marketById } = useCatalog();
  const [group, setGroup] = useState<GroupDetail | null | undefined>(undefined);
  const groupId = item?.group_id;

  useEffect(() => {
    if (groupId == null) return;
    let live = true;
    api.productGroup(groupId).then(g => { if (live) setGroup(g); }).catch(() => { if (live) setGroup(null); });
    return () => { live = false; setGroup(undefined); };
  }, [groupId]);

  const offers = useMemo<Offer[]>(() => (group?.products ?? [])
    .filter(p => p.price != null && p.is_available)
    .flatMap(p => p.store_prices.length
      ? p.store_prices.map(sp => ({ key: `${p.id}-${sp.store_id}`, productId: p.id, brand: p.brand, name: p.name, marketId: p.market_id, store: sp.store_name as string | null, price: num(sp.price) }))
      : [{ key: String(p.id), productId: p.id, brand: p.brand, name: p.name, marketId: p.market_id, store: p.store_name, price: num(p.price) }])
    .sort((a, b) => a.price - b.price), [group]);

  // Her markanın en ucuz fiyatı
  const brands = useMemo(() => {
    const best = new Map<string, number>();
    for (const o of offers) if (o.brand && (best.get(o.brand) ?? Infinity) > o.price) best.set(o.brand, o.price);
    return [...best.entries()].sort((a, b) => a[1] - b[1]);
  }, [offers]);

  if (!item) return null;
  const anything = item.preferred_product_id == null && item.preferred_brand == null;
  const brandOnly = item.preferred_product_id == null && item.preferred_brand != null;

  const option = (key: string, selected: boolean, onPress: () => void, content: ReactNode) => (
    <Pressable key={key} onPress={onPress} accessibilityRole="button" accessibilityState={{ selected }}
      style={{ flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 12, paddingHorizontal: 14, borderRadius: 14,
        backgroundColor: selected ? t.tintSoft : t.card, borderWidth: 1, borderColor: selected ? t.tint : t.border }}>
      {content}
      <Icon name={selected ? 'check-circle' : 'circle'} size={20} color={selected ? t.tint : t.border} />
    </Pressable>
  );
  const label = (text: string) => <Text style={{ color: t.textMuted, fontSize: 13, fontWeight: '800', letterSpacing: 0.4, marginTop: 4 }}>{text}</Text>;

  return (
    <Modal visible transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.45)' }} onPress={onClose} />
      <View style={{ backgroundColor: t.background, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, paddingBottom: 20 + insets.bottom, gap: 10, maxHeight: '80%' }}>
        <Text style={{ color: t.text, fontWeight: '800', fontSize: 18 }} numberOfLines={2}>{item.group_name}</Text>
        <Muted>Seçtikleriniz “Tek market”, “En yakın” ve “Birkaç market” planlarında korunur. “En ucuz” planı seçimlerinizi yok sayıp her ürünün en ucuzunu verir.</Muted>
        {group === undefined && <ActivityIndicator color={t.tint} style={{ padding: 20 }} />}
        {group === null && <Text style={{ color: t.danger }}>Ürünler yüklenemedi.</Text>}
        {group && (
          <ScrollView style={{ flexShrink: 1 }} contentContainerStyle={{ gap: 8 }}>
            {option('any', anything, () => onPick({ preferred_product_id: null }), (
              <View style={{ flex: 1 }}>
                <Text style={{ color: t.text, fontWeight: '700' }}>Farketmez (en ucuzu)</Text>
                {offers[0] && <Muted>En ucuz {formatTL(offers[0].price)} ₺</Muted>}
              </View>
            ))}
            {brands.length > 1 && label('MARKA SEÇ (HER MARKETTE EN UCUZU)')}
            {brands.length > 1 && brands.map(([brand, price]) => option(`b-${brand}`, brandOnly && item.preferred_brand === brand,
              () => onPick({ preferred_brand: brand }), (
                <View style={{ flex: 1 }}>
                  <Text style={{ color: t.text, fontWeight: '700' }}>{brand}</Text>
                  <Muted>En ucuz {formatTL(price)} ₺</Muted>
                </View>
              )))}
            {label('BELİRLİ MARKET VE ÜRÜN')}
            {offers.map(o => option(o.key, item.preferred_product_id === o.productId, () => onPick({ preferred_product_id: o.productId }), (
              <>
                <MarketBadge id={o.marketId} size={28} />
                <View style={{ flex: 1 }}>
                  <Text style={{ color: t.text, fontWeight: '600' }} numberOfLines={1}>{marketById(o.marketId)?.name}{o.store ? ` · ${o.store}` : ''}</Text>
                  <Muted>{o.brand ? `${o.brand} · ` : ''}{o.name}</Muted>
                </View>
                <Text style={{ color: t.text, fontWeight: '800' }}>{formatTL(o.price)} ₺</Text>
              </>
            )))}
            {offers.length === 0 && <Muted>Seçili marketlerinde bu ürün şu an bulunamadı.</Muted>}
          </ScrollView>
        )}
      </View>
    </Modal>
  );
}
