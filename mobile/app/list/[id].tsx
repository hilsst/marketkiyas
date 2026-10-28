import { router, Stack, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useCallback, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Alert, Platform, Pressable, Text, View } from 'react-native';

import Celebration from '@/components/Celebration';
import MarketBadge from '@/components/MarketBadge';
import ProductImage from '@/components/ProductImage';
import { Button, Card, Muted, Screen, useTheme } from '@/components/ui';
import { api, CompleteResponse, ItemPatch, ListDetail, ListItem, num, OptimizeResult, Plan, PlanType } from '@/lib/api';
import { useCatalog } from '@/lib/catalog';

type Tab = 'items' | 'optimize';
const MODES: { key: PlanType; label: string }[] = [
  { key: 'single_market', label: 'Tek Market' },
  { key: 'combination', label: 'Kombinasyon' },
  { key: 'opportunist', label: 'Fırsatçı 🚀' },
];

/** Geri alınamaz işlemler için onay (web önizlemesinde Alert yok, confirm kullanılır) */
function confirmAsk(title: string, message: string, onYes: () => void) {
  if (Platform.OS === 'web') {
    if (globalThis.confirm?.(`${title}\n\n${message}`)) onYes();
    return;
  }
  Alert.alert(title, message, [{ text: 'Vazgeç', style: 'cancel' }, { text: 'Evet', style: 'destructive', onPress: onYes }]);
}

/**
 * Liste ekranı (web'deki lists/[id] sayfasının telefon hâli): ürünler, Tek Market / Kombinasyon / Fırsatçı planları,
 * plan uygulanınca markete göre alışveriş modu ve "Alışverişi Bitir" kutlaması.
 */
export default function ListScreen() {
  const t = useTheme();
  const { id } = useLocalSearchParams<{ id: string }>();
  const listId = Number(id);
  const { marketById, categoryIcon } = useCatalog();
  const [detail, setDetail] = useState<ListDetail | null | undefined>(undefined);
  const [opt, setOpt] = useState<OptimizeResult | null>(null);
  const [tab, setTab] = useState<Tab>('items');
  const [mode, setMode] = useState<PlanType>('single_market');
  const [error, setError] = useState<string | null>(null);
  const [finishing, setFinishing] = useState(false);
  const [celebration, setCelebration] = useState<CompleteResponse | null>(null);
  const seq = useRef(0);

  const reoptimize = useCallback(() => { api.optimize(listId).then(setOpt).catch(() => {}); }, [listId]);
  const load = useCallback(() => {
    api.list(listId).then(setDetail).catch(() => setDetail(null));
    reoptimize();
  }, [listId, reoptimize]);
  // Ürün ekleyip geri dönünce liste tazelensin
  useFocusEffect(load);

  /** Sunucu değişikliği: son isteğin cevabı ekrana yazılır, kalem değişince planlar yeniden hesaplanır */
  const mutate = async (call: () => Promise<ListDetail>, reopt = true) => {
    const mine = ++seq.current;
    setError(null);
    try {
      const fresh = await call();
      if (mine === seq.current) setDetail(fresh);
      if (reopt) reoptimize();
      return fresh;
    } catch (e) {
      setError((e as Error).message);
      return null;
    }
  };
  const update = (itemId: number, patch: ItemPatch) => mutate(() => api.updateItem(listId, itemId, patch), !('is_checked' in patch && Object.keys(patch).length === 1));
  const remove = (itemId: number) => mutate(() => api.removeItem(listId, itemId));

  const plan: Plan | null = opt ? (mode === 'single_market' ? opt.single_market.plan : mode === 'combination' ? opt.combination : opt.opportunist) : null;
  const comboLines = useMemo(() => new Map((opt?.combination.lines ?? []).map(l => [l.item_id, l])), [opt]);

  if (celebration) {
    return (
      <Celebration savedAmount={num(celebration.saved_amount)} shoppingSavings={num(celebration.shopping_savings)}
        vaultTotal={num(celebration.vault_total)} note={celebration.note}
        onDone={() => { setCelebration(null); router.replace('/'); }} />
    );
  }
  if (detail === undefined) return <Screen safeTop={false}><ActivityIndicator color={t.tint} style={{ marginTop: 40 }} /></Screen>;
  if (detail === null) return <Screen safeTop={false}><Muted>Liste bulunamadı.</Muted></Screen>;

  const list = detail;
  const total = list.items.length;
  const checked = list.items.filter(i => i.is_checked).length;
  const shopping = list.applied_plan != null;
  const itemById = new Map(list.items.map(i => [i.id, i]));

  const finish = async () => {
    if (finishing) return;
    setFinishing(true);
    try { setCelebration(await api.complete(list.id)); } catch (e) { setError((e as Error).message); } finally { setFinishing(false); }
  };
  const apply = async () => {
    const applied = await mutate(() => api.applyPlan(list.id, mode), false);
    if (applied) setTab('items');
  };
  const deleteList = () => confirmAsk('Liste silinsin mi?', 'Kaydettiğin tasarruflar Profil sayfanda kalır.', async () => {
    try { await api.deleteList(list.id); router.back(); } catch (e) { setError((e as Error).message); }
  });
  const blocked = shopping
    ? 'Plan uygulandı. Alışverişi Ürünler sekmesindeki "Alışverişi Bitir" ile tamamla.'
    : total > 0 && checked === total ? 'Tüm ürünler alınmış görünüyor. Yeni alışveriş için işaretleri kaldır.' : null;
  const applyDisabled = blocked != null || total === 0 || (mode === 'single_market' && !opt?.single_market.available);

  const row = (it: ListItem, inShopping: boolean) => {
    const line = comboLines.get(it.id);
    const locked = it.preferred_product_id != null || it.preferred_brand != null;
    const qty = num(it.quantity);
    return (
      <View key={it.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, borderTopWidth: 1, borderTopColor: t.border, opacity: it.is_checked ? 0.5 : 1 }}>
        <Pressable onPress={() => update(it.id, { is_checked: !it.is_checked })} hitSlop={8} accessibilityRole="checkbox" accessibilityState={{ checked: it.is_checked }}
          style={{ width: 26, height: 26, borderRadius: 8, borderWidth: 2, borderColor: t.tint, backgroundColor: it.is_checked ? t.tint : 'transparent', alignItems: 'center', justifyContent: 'center' }}>
          {it.is_checked && <Text style={{ color: '#fff', fontWeight: '900' }}>✓</Text>}
        </Pressable>
        <ProductImage uri={it.image_url} icon={categoryIcon(it.category_id)} size={40} />
        <View style={{ flex: 1 }}>
          <Text style={{ color: t.text, fontWeight: '600', textDecorationLine: it.is_checked ? 'line-through' : 'none' }} numberOfLines={2}>{it.group_name}</Text>
          {inShopping ? (
            <Muted>{[it.assigned?.brand || it.assigned?.product_name, it.assigned?.store_name].filter(Boolean).join(' · ')} × {qty}</Muted>
          ) : (
            <Muted>{locked ? `🔒 ${line?.brand || it.preferred_brand || 'seçili ürün'}` : 'Farketmez (en ucuzu)'}{line ? ` · ${num(line.unit_price).toFixed(2)} ₺` : ''}</Muted>
          )}
        </View>
        {inShopping ? (
          <Text style={{ color: t.text, fontWeight: '800' }}>{(num(it.assigned?.unit_price) * qty).toFixed(2)} ₺</Text>
        ) : (
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
            <Pressable onPress={() => (qty > 1 ? update(it.id, { quantity: qty - 1 }) : remove(it.id))} hitSlop={6}
              style={{ width: 30, height: 30, borderRadius: 15, backgroundColor: qty > 1 ? t.border : '#fee2e2', alignItems: 'center', justifyContent: 'center' }}>
              <Text style={{ color: qty > 1 ? t.text : '#dc2626', fontWeight: '800' }}>{qty > 1 ? '−' : '🗑'}</Text>
            </Pressable>
            <Text style={{ color: t.text, fontWeight: '700', minWidth: 18, textAlign: 'center' }}>{qty}</Text>
            <Pressable onPress={() => qty < 99 && update(it.id, { quantity: qty + 1 })} hitSlop={6}
              style={{ width: 30, height: 30, borderRadius: 15, backgroundColor: t.border, alignItems: 'center', justifyContent: 'center' }}>
              <Text style={{ color: t.text, fontWeight: '800' }}>+</Text>
            </Pressable>
          </View>
        )}
      </View>
    );
  };

  return (
    <Screen safeTop={false}>
      <Stack.Screen options={{ title: list.name, headerRight: () => (
        <Text onPress={deleteList} style={{ color: t.danger, fontWeight: '600', paddingHorizontal: 8 }}>Sil</Text>
      ) }} />
      <Muted>{total} ürün · alınan {checked}/{total}</Muted>

      <View style={{ flexDirection: 'row', backgroundColor: t.border, borderRadius: 12, padding: 4 }}>
        {(['items', 'optimize'] as Tab[]).map(k => (
          <Pressable key={k} onPress={() => setTab(k)} style={{ flex: 1, paddingVertical: 10, borderRadius: 9, alignItems: 'center', backgroundColor: tab === k ? t.card : 'transparent' }}>
            <Text style={{ color: tab === k ? t.tint : t.textMuted, fontWeight: '700' }}>{k === 'items' ? 'Ürünler' : 'Planlar'}</Text>
          </Pressable>
        ))}
      </View>
      {error && <Text style={{ color: t.danger }}>{error}</Text>}

      {tab === 'items' && shopping && (
        <>
          <Card style={{ backgroundColor: t.tint, borderColor: t.tint, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
            <Text style={{ color: '#fff', fontWeight: '700' }}>🛒 Alışveriş modu · {checked}/{total} alındı</Text>
            <Text onPress={() => mutate(() => api.cancelPlan(list.id), false)} style={{ color: '#fff', fontWeight: '700', textDecorationLine: 'underline' }}>İptal Et</Text>
          </Card>
          {list.shopping_groups.filter(g => g.market_id != null).map(g => {
            const items = g.item_ids.map(i => itemById.get(i)).filter((i): i is ListItem => !!i);
            const sum = items.reduce((s, i) => s + num(i.assigned?.unit_price) * num(i.quantity), 0);
            return (
              <Card key={g.market_id} style={{ padding: 0 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, padding: 12 }}>
                  <MarketBadge id={g.market_id} size={26} />
                  <Text style={{ color: t.text, fontWeight: '800', flex: 1 }}>{marketById(g.market_id)?.name}</Text>
                  <Text style={{ color: t.text, fontWeight: '800' }}>{sum.toFixed(2)} ₺</Text>
                </View>
                {items.map(i => row(i, true))}
              </Card>
            );
          })}
          <Button title={finishing ? 'Kaydediliyor…' : '✅ Alışverişi Bitir ve Tasarrufu Kaydet'} onPress={finish} busy={finishing} />
          <Muted style={{ textAlign: 'center' }}>Bir liste haftada bir kez tasarruf kasasına eklenir.</Muted>
        </>
      )}

      {tab === 'items' && !shopping && (
        <>
          <Card style={{ padding: 0 }}>
            {list.items.length === 0 && <Muted style={{ padding: 16 }}>Liste boş. Aşağıdan ürün ekle.</Muted>}
            {list.items.map(i => row(i, false))}
          </Card>
          <Button title="+ Ürün ekle" kind="secondary" onPress={() => router.push({ pathname: '/search', params: { listId: String(list.id) } })} />
          {total > 0 && <Button title="Planları gör" onPress={() => setTab('optimize')} />}
        </>
      )}

      {tab === 'optimize' && (
        <>
          <View style={{ flexDirection: 'row', gap: 6 }}>
            {MODES.map(m => (
              <Pressable key={m.key} onPress={() => setMode(m.key)} style={{ flex: 1, paddingVertical: 9, borderRadius: 10, alignItems: 'center',
                borderWidth: 1, borderColor: mode === m.key ? t.tint : t.border, backgroundColor: mode === m.key ? t.tint : t.card }}>
                <Text style={{ color: mode === m.key ? '#fff' : t.text, fontWeight: '600', fontSize: 13 }}>{m.label}</Text>
              </Pressable>
            ))}
          </View>
          {!opt && <ActivityIndicator color={t.tint} />}
          {opt && (
            <Card style={{ gap: 10 }}>
              <Muted>{mode === 'single_market' ? 'Tek markette, seçimlerinle' : mode === 'combination' ? 'Seçtiğin markalarla, en ucuz marketlerden' : 'Marka fark etmeden, her ürünün en ucuzu'}</Muted>
              <Text style={{ color: t.text, fontSize: 30, fontWeight: '900' }}>{plan ? `${num(plan.total).toFixed(2)} ₺` : '—'}</Text>
              {mode === 'single_market' && !opt.single_market.available && (
                <Text style={{ color: '#c2410c' }}>⚠️ {opt.single_market.warning || 'Hiçbir market listedeki tüm ürünleri satmıyor.'}</Text>
              )}
              {mode === 'opportunist' && num(opt.savings.weekly) > 0 && (
                <Text style={{ color: t.tint, fontWeight: '700' }}>Seçimlerine göre {num(opt.savings.weekly).toFixed(2)} ₺ daha ucuz (yılda ~{num(opt.savings.yearly).toFixed(0)} ₺)</Text>
              )}
              {plan?.by_market.map(b => (
                <View key={b.market_id} style={{ gap: 4, borderTopWidth: 1, borderTopColor: t.border, paddingTop: 8 }}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                    <MarketBadge id={b.market_id} size={22} />
                    <Text style={{ color: t.text, fontWeight: '700', flex: 1 }}>{marketById(b.market_id)?.name}</Text>
                    <Text style={{ color: t.text, fontWeight: '800' }}>{num(b.total).toFixed(2)} ₺</Text>
                  </View>
                  {plan.lines.filter(l => b.item_ids.includes(l.item_id)).map(l => (
                    <View key={l.item_id} style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 8 }}>
                      <Muted style={{ flex: 1 }}>{l.group_name} ({l.substituted ? l.product_name : l.brand || l.product_name}){l.substituted ? ' · benzeri alındı' : ''}</Muted>
                      <Muted>{num(l.line_total).toFixed(2)} ₺</Muted>
                    </View>
                  ))}
                </View>
              ))}
              {mode === 'single_market' && (
                <View style={{ gap: 2, borderTopWidth: 1, borderTopColor: t.border, paddingTop: 8 }}>
                  {opt.single_market.markets.filter(m => m.found > 0).map(m => (
                    <Muted key={m.market_id}>
                      {marketById(m.market_id)?.name}: {num(m.total).toFixed(2)} ₺{m.substituted ? ` · ${m.substituted} farklı marka` : ''}{m.missing ? ` · ${m.missing} ürün yok` : ''}
                    </Muted>
                  ))}
                </View>
              )}
            </Card>
          )}
          <Button title="🛒 Bu planı alışveriş listeme uygula" onPress={apply} disabled={applyDisabled} />
          {blocked && <Muted style={{ textAlign: 'center' }}>{blocked}</Muted>}
        </>
      )}
    </Screen>
  );
}
