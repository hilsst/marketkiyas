import { router, Stack, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useCallback, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Alert, Linking, Platform, Pressable, Share, Text, View } from 'react-native';

import Celebration from '@/components/Celebration';
import MarketBadge from '@/components/MarketBadge';
import ProductImage from '@/components/ProductImage';
import Icon from '@/components/Icon';
import ItemPicker from '@/components/ItemPicker';
import { ActionBar, Button, Card, Muted, Screen, Segmented, useTheme } from '@/components/ui';
import { api, CompleteResponse, Store, ItemPatch, ListDetail, ListItem, num, OptimizeResult, Plan, PlanType } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { useCatalog } from '@/lib/catalog';
import { Coords, distanceKm, formatKm, getCoords, LocationResult } from '@/lib/location';
import { accountRedirect } from '@/lib/guest';
import { formatTL } from '@/lib/format';

type Tab = 'items' | 'optimize';
const SYNC_MS = 8000; // ortak listede diğer üyelerin değişiklikleri bu aralıkla çekilir
const MODES: { key: PlanType; label: string }[] = [
  { key: 'single_market', label: 'Tek market' },
  { key: 'nearby', label: 'En yakın' },
  { key: 'combination', label: 'Birkaç market' },
  { key: 'opportunist', label: 'En ucuz' },
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
  const { user } = useAuth();
  const [sharing, setSharing] = useState(false);
  const [detail, setDetail] = useState<ListDetail | null | undefined>(undefined);
  const [opt, setOpt] = useState<OptimizeResult | null>(null);
  const [tab, setTab] = useState<Tab>('items');
  const [pickedMode, setMode] = useState<PlanType>('single_market');
  const [error, setError] = useState<string | null>(null);
  const [myPos, setMyPos] = useState<Coords | null>(null);
  const [stores, setStores] = useState<Store[]>([]);
  const [pickItem, setPickItem] = useState<ListItem | null>(null);
  const [finishing, setFinishing] = useState(false);
  const [celebration, setCelebration] = useState<CompleteResponse | null>(null);
  const seq = useRef(0);
  // Yakın Market için konum: Fiyatlar sekmesi ilk açıldığında sorulur, yalnız hesaplamada kullanılır
  const coords = useRef<Coords | null>(null);
  const [loc, setLoc] = useState<'idle' | 'asking' | LocationResult['reason'] | 'ready'>('idle');

  const reoptimize = useCallback(() => { api.optimize(listId, coords.current).then(setOpt).catch(() => {}); }, [listId]);
  const askLocation = useCallback(async () => {
    setLoc('asking');
    const r = await getCoords();
    coords.current = r.coords;
    setMyPos(r.coords);
    setLoc(r.coords ? 'ready' : r.reason);
    if (r.coords) reoptimize();
  }, [reoptimize]);
  const openTab = (k: Tab) => { setTab(k); if (k === 'optimize' && loc !== 'ready' && loc !== 'asking') void askLocation(); };
  const load = useCallback(() => {
    // Alışveriş modundaki liste şube mesafelerini de gösterir: konum yalnız bir kez, izin yoksa sessizce atlanır
    api.list(listId).then(d => { setDetail(d); if (d.applied_plan != null) void getCoords().then(r => setMyPos(r.coords)); }).catch(() => setDetail(null));
    api.myStores().then(setStores).catch(() => {});
    reoptimize();
  }, [listId, reoptimize]);
  // Ürün ekleyip geri dönünce liste tazelensin; ortak listede ekran açıkken diğer telefonun eklediği ürünler de gelsin
  useFocusEffect(useCallback(() => {
    load();
    const timer = setInterval(() => {
      api.list(listId).then(fresh => {
        setDetail(prev => (prev && prev.updated_at === fresh.updated_at ? prev : fresh));
      }).catch(() => {});
    }, SYNC_MS);
    return () => clearInterval(timer);
  }, [load, listId]));

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

  // "Birkaç market" yalnız markası seçilmiş ürün varsa anlamlı: markasızken "En ucuz" ile aynı sonucu verir
  const hasBrandChoice = !!detail?.items.some(i => i.preferred_product_id != null || i.preferred_brand != null);
  const mode: PlanType = pickedMode === 'combination' && !hasBrandChoice ? 'single_market' : pickedMode;
  const modes = hasBrandChoice ? MODES : MODES.filter(m => m.key !== 'combination');
  const plan: Plan | null = opt ? (mode === 'single_market' ? opt.single_market.plan : mode === 'nearby' ? opt.nearby : mode === 'combination' ? opt.combination : opt.opportunist) : null;
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
  const onCard = mode === 'opportunist' ? '#fff' : t.onTint; // plan kartı: turuncuda beyaz, yeşilde (koyu temada açık yeşil) koyu yazı
  const total = list.items.length;
  const checked = list.items.filter(i => i.is_checked).length;
  const shopping = list.applied_plan != null;
  // Alışverişi bitirilen liste kilitli: ürün eklenmez, "Tekrar kullan" ile yeniden açılır
  const completed = list.status === 'completed';
  const itemById = new Map(list.items.map(i => [i.id, i]));

  // Alışverişi bitirmek tasarrufu kasaya kaydeder: misafirden hesap istenen an (liste ve ürünler olduğu gibi kalır)
  const finish = async () => {
    if (finishing) return;
    const toAccount = accountRedirect(user, 'save');
    if (toAccount) { router.push(toAccount); return; }
    setFinishing(true);
    try { setCelebration(await api.complete(list.id)); } catch (e) { setError((e as Error).message); } finally { setFinishing(false); }
  };
  const apply = async () => {
    const applied = await mutate(() => api.applyPlan(list.id, mode, coords.current), false);
    if (applied) setTab('items');
  };
  const isOwner = list.owner_id === user?.id;
  const deleteList = () => confirmAsk('Liste silinsin mi?', 'Kaydettiğiniz tasarruflar Profil sayfanızda kalır.', async () => {
    try { await api.deleteList(list.id); router.back(); } catch (e) { setError((e as Error).message); }
  });
  const leaveList = () => confirmAsk('Listeden ayrılınsın mı?', 'Liste sahibinde kalmaya devam eder.', async () => {
    try { if (user) await api.removeMember(list.id, user.id); router.back(); } catch (e) { setError((e as Error).message); }
  });
  /** Davet kodunu oluşturur ve telefonun paylaş penceresini açar (WhatsApp, SMS…) */
  const shareInvite = async () => {
    const toAccount = accountRedirect(user, 'share');
    if (toAccount) { router.push(toAccount); return; }
    try {
      const code = list.share_code || (await api.shareList(list.id)).share_code;
      setDetail({ ...list, share_code: code });
      await Share.share({ message: `"${list.name}" alışveriş listeme katılın! Ucuzu'da Listeler > "Kodla ortak listeye katıl" deyip bu kodu yazın: ${code}` });
    } catch (e) { setError((e as Error).message); }
  };
  const blocked = shopping
    ? 'Plan uygulandı. Alışverişi Ürünler sekmesindeki "Alışverişi bitir" düğmesiyle tamamlayın.'
    : total > 0 && checked === total ? 'Tüm ürünler alınmış görünüyor. Yeni alışveriş için işaretleri kaldırın.' : null;
  const applyDisabled = blocked != null || total === 0 || (mode === 'single_market' && !opt?.single_market.available) || (mode === 'nearby' && !opt?.nearby);

  const row = (it: ListItem, inShopping: boolean) => {
    const line = comboLines.get(it.id);
    const locked = it.preferred_product_id != null || it.preferred_brand != null;
    const qty = num(it.quantity);
    return (
      <View key={it.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, borderTopWidth: 1, borderTopColor: t.border, opacity: it.is_checked ? 0.7 : 1 }}>
        <Pressable onPress={() => update(it.id, { is_checked: !it.is_checked })} hitSlop={10} accessibilityRole="checkbox" accessibilityLabel={`${it.group_name} alındı`} accessibilityState={{ checked: it.is_checked }}
          style={{ width: 32, height: 32, borderRadius: 10, borderWidth: 2, borderColor: it.is_checked ? t.tint : t.border, backgroundColor: it.is_checked ? t.tint : 'transparent', alignItems: 'center', justifyContent: 'center' }}>
          {it.is_checked && <Icon name="check" size={20} color={t.onTint} />}
        </Pressable>
        <ProductImage uri={it.image_url} icon={categoryIcon(it.category_id)} size={40} />
        <Pressable disabled={inShopping} onPress={() => setPickItem(it)} accessibilityRole="button" accessibilityLabel={`${it.group_name} için market ve marka seçin`}
          style={{ flex: 1 }}>
          <Text style={{ color: t.text, fontWeight: '600', textDecorationLine: it.is_checked ? 'line-through' : 'none' }} numberOfLines={2}>{it.group_name}</Text>
          {it.added_by_id != null && it.added_by_id !== user?.id && it.added_by_name && (
            <Text style={{ color: '#075985', fontSize: 14, fontWeight: '600' }}>{it.added_by_name} ekledi</Text>
          )}
          {inShopping ? (
            <Muted>{[it.assigned?.brand || it.assigned?.product_name, it.assigned?.store_name].filter(Boolean).join(' · ')} × {qty}</Muted>
          ) : (
            <Text style={{ color: locked ? t.tintDark : t.textMuted, fontSize: 14, fontWeight: locked ? '700' : '400' }}>
              {locked ? `Seçili: ${line?.brand || it.preferred_brand || 'seçili ürün'}` : 'Farketmez (en ucuzu)'}{line ? ` · ${formatTL(num(line.unit_price))} ₺` : ''}  ›
            </Text>
          )}
        </Pressable>
        {inShopping ? (
          <Text style={{ color: t.text, fontWeight: '800' }}>{formatTL((num(it.assigned?.unit_price) * qty))} ₺</Text>
        ) : (
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <Pressable
              onPress={() => (qty > 1 ? update(it.id, { quantity: qty - 1 })
                : confirmAsk('Ürün listeden çıkarılsın mı?', `${it.group_name} listeden silinecek.`, () => { void remove(it.id); }))}
              hitSlop={4} accessibilityRole="button" accessibilityLabel={qty > 1 ? `${it.group_name} adedini azalt` : `${it.group_name} ürününü listeden çıkar`}
              style={{ width: 38, height: 38, borderRadius: 19, backgroundColor: qty > 1 ? t.background : '#fee2e2', alignItems: 'center', justifyContent: 'center' }}>
              <Icon name={qty > 1 ? 'minus' : 'trash-2'} size={18} color={qty > 1 ? t.text : '#B91C1C'} />
            </Pressable>
            <Text style={{ color: t.text, fontWeight: '700', minWidth: 22, textAlign: 'center', fontSize: 16 }}>{qty}</Text>
            <Pressable onPress={() => qty < 99 && update(it.id, { quantity: qty + 1 })} hitSlop={4}
              accessibilityRole="button" accessibilityLabel={`${it.group_name} adedini artır`}
              style={{ width: 38, height: 38, borderRadius: 19, backgroundColor: t.background, alignItems: 'center', justifyContent: 'center' }}>
              <Icon name="plus" size={18} color={t.text} />
            </Pressable>
          </View>
        )}
      </View>
    );
  };

  /** Planın o marketten alacağı şubeler: ad, konuma göre mesafe (konum izni varsa) ve haritada aç */
  const here = myPos;
  const storeInfo = (ids: number[]) => {
    return [...new Set(ids)].map(id => stores.find(s => s.id === id)).filter((s): s is Store => s != null).map(s => {
      const at = s.latitude != null && s.longitude != null ? { lat: num(s.latitude), lon: num(s.longitude) } : null;
      const km = here && at ? distanceKm(here, at) : null;
      return (
        <Pressable key={s.id} disabled={!at} accessibilityRole="link" accessibilityLabel={`${s.name} haritada aç`}
          onPress={() => at && Linking.openURL(Platform.OS === 'ios' ? `http://maps.apple.com/?ll=${at.lat},${at.lon}&q=${encodeURIComponent(s.name)}` : `https://www.google.com/maps/search/?api=1&query=${at.lat},${at.lon}`)}
          style={{ flexDirection: 'row', alignItems: 'center', gap: 6, paddingBottom: 4 }}>
          <Icon name="map-pin" size={14} color={t.tint} />
          <Text style={{ color: t.textMuted, fontSize: 14, flex: 1 }} numberOfLines={1}>{s.name}{km != null ? ` · ${formatKm(km)}` : ''}</Text>
          {at && <Text style={{ color: t.tint, fontSize: 13, fontWeight: '700' }}>Haritada aç</Text>}
        </Pressable>
      );
    });
  };

  const footer = completed ? (
    <ActionBar>
      <Button title="Listeyi tekrar kullan" onPress={() => mutate(() => api.reopenList(list.id))} />
      <Muted style={{ textAlign: 'center' }}>Aynı ürünlerle yeni bir alışverişe başlar, işaretler sıfırlanır.</Muted>
    </ActionBar>
  ) : tab === 'items' && shopping ? (
    <ActionBar>
      <Button title={finishing ? 'Kaydediliyor…' : 'Alışverişi bitir'} onPress={finish} busy={finishing} />
      <Muted style={{ textAlign: 'center' }}>Bir liste haftada bir kez tasarruf kasasına eklenir.</Muted>
    </ActionBar>
  ) : tab === 'items' ? (
    <ActionBar>
      <Button title="+ Ürün ekle" kind="secondary" onPress={() => router.push({ pathname: '/search', params: { listId: String(list.id) } })} />
      {total > 0 && <Button title="En ucuzunu bul" onPress={() => openTab('optimize')} />}
    </ActionBar>
  ) : (
    <ActionBar>
      <Button title="Bu planla alışverişe başla" onPress={apply} disabled={applyDisabled} />
      {blocked && <Muted style={{ textAlign: 'center' }}>{blocked}</Muted>}
    </ActionBar>
  );

  return (
    <Screen safeTop={false} footer={footer}>
      <Stack.Screen options={{ title: list.name, headerRight: () => (
        <View style={{ flexDirection: 'row', gap: 6, paddingHorizontal: 4 }}>
          <Pressable onPress={() => setSharing(v => !v)} accessibilityRole="button" accessibilityLabel="Listeyi paylaş"
            style={{ minHeight: 44, minWidth: 44, justifyContent: 'center' }}>
            <Text style={{ color: t.tintDark, fontWeight: '700', fontSize: 16 }}>Paylaş</Text>
          </Pressable>
          <Pressable onPress={isOwner ? deleteList : leaveList} accessibilityRole="button" accessibilityLabel={isOwner ? 'Listeyi sil' : 'Listeden ayrıl'}
            style={{ minHeight: 44, minWidth: 44, justifyContent: 'center' }}>
            <Text style={{ color: t.danger, fontWeight: '600', fontSize: 16 }}>{isOwner ? 'Sil' : 'Ayrıl'}</Text>
          </Pressable>
        </View>
      ) }} />
      <Muted>{total} ürün · alınan {checked}/{total}{list.members.length > 0 || !isOwner ? ' · ortak liste' : ''}</Muted>

      {sharing && (
        <Card style={{ gap: 10 }}>
          <Text style={{ color: t.text, fontWeight: '800', fontSize: 16 }}>Ortak liste</Text>
          <Muted>Kodu alan kişi kendi telefonunda bu listeyi görür, ürün ekler ve işaretler. Değişiklikler birkaç saniyede herkese yansır.</Muted>
          {list.share_code && (
            <Text selectable style={{ color: t.text, fontSize: 28, fontWeight: '900', letterSpacing: 4, textAlign: 'center' }}>{list.share_code}</Text>
          )}
          {isOwner && <Button title="Davet gönder (WhatsApp, SMS…)" onPress={shareInvite} />}
          <View style={{ gap: 4 }}>
            <Text style={{ color: t.text, fontWeight: '700' }}>Listedekiler</Text>
            <Muted>{list.owner_name || 'Sahip'}{isOwner ? ' (siz)' : ''} · sahibi</Muted>
            {list.members.map(m => (
              <View key={m.user_id} style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                <Muted>{m.name || 'Üye'}{m.user_id === user?.id ? ' (siz)' : ''}</Muted>
                {isOwner && <Text onPress={() => confirmAsk('Üye çıkarılsın mı?', `${m.name || 'Üye'} bu listeyi artık görmez.`, () => {
                  api.removeMember(list.id, m.user_id).then(load).catch(e => setError(e.message));
                })} style={{ color: t.danger }}>Çıkar</Text>}
              </View>
            ))}
            {list.members.length === 0 && <Muted>Henüz kimse katılmadı.</Muted>}
          </View>
        </Card>
      )}

      {!completed && <Segmented value={tab} onChange={openTab} options={[{ key: 'items', label: 'Ürünler' }, { key: 'optimize', label: 'Fiyatlar' }]} />}
      {error && <Text style={{ color: t.danger }}>{error}</Text>}

      {completed && (
        <>
          <Card style={{ gap: 4, borderColor: t.tint, borderWidth: 2 }}>
            <Text style={{ color: t.tint, fontSize: 16, fontWeight: '800' }}>Alışveriş tamamlandı</Text>
            <Muted>
              {list.completed_at ? new Date(list.completed_at).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', weekday: 'long' }) + ' · ' : ''}
              Bu listeye artık ürün eklenemez.
            </Muted>
          </Card>
          <Card style={{ padding: 0 }}>
            {list.items.map(i => (
              <View key={i.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, borderBottomWidth: 1, borderBottomColor: t.border }}>
                <Icon name={i.is_checked ? 'check-square' : 'square'} size={18} color={i.is_checked ? t.tint : t.textMuted} />
                <Text style={{ color: t.text, flex: 1 }} numberOfLines={2}>{i.group_name}</Text>
                <Muted>{num(i.quantity)} adet</Muted>
              </View>
            ))}
          </Card>
        </>
      )}

      {!completed && tab === 'items' && shopping && (
        <>
          <Card style={{ backgroundColor: t.tint, borderColor: t.tint, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
            <Text style={{ color: t.onTint, fontWeight: '700' }}>Alışveriş modu · {checked}/{total} alındı</Text>
            <Text onPress={() => mutate(() => api.cancelPlan(list.id), false)} style={{ color: t.onTint, fontWeight: '700', textDecorationLine: 'underline' }}>İptal Et</Text>
          </Card>
          {list.shopping_groups.filter(g => g.market_id != null).map(g => {
            const items = g.item_ids.map(i => itemById.get(i)).filter((i): i is ListItem => !!i);
            const sum = items.reduce((s, i) => s + num(i.assigned?.unit_price) * num(i.quantity), 0);
            return (
              <Card key={g.market_id} style={{ padding: 0 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, padding: 12 }}>
                  <MarketBadge id={g.market_id} size={26} />
                  <Text style={{ color: t.text, fontWeight: '800', flex: 1 }}>{marketById(g.market_id)?.name}</Text>
                  <Text style={{ color: t.text, fontWeight: '800' }}>{formatTL(sum)} ₺</Text>
                </View>
                <View style={{ paddingHorizontal: 12 }}>{storeInfo(items.map(i => i.assigned?.store_id).filter((x): x is number => x != null))}</View>
                {items.map(i => row(i, true))}
              </Card>
            );
          })}
        </>
      )}

      {!completed && tab === 'items' && !shopping && (
        <>
          <Card style={{ padding: 0 }}>
            {list.items.length === 0 && <Muted style={{ padding: 16 }}>Liste boş. Aşağıdaki “+ Ürün ekle” düğmesine dokunun.</Muted>}
            {list.items.map(i => row(i, false))}
          </Card>
        </>
      )}

      {!completed && tab === 'optimize' && (
        <>
          <Segmented value={mode} onChange={setMode} options={modes} />
          {!opt && <ActivityIndicator color={t.tint} />}
          {opt && (
            <>
              {!(mode === 'nearby' && !opt.nearby) && <View style={{ borderRadius: 22, padding: 20, gap: 4, backgroundColor: mode === 'opportunist' ? t.accent : t.tint }}>
                <Text style={{ color: onCard, fontSize: 14 }}>{mode === 'single_market' ? 'Tek markette, seçtiğiniz markalarla' : mode === 'nearby' ? 'Size en yakın marketlerden' : mode === 'combination' ? 'Seçtiğiniz markalarla, birkaç marketten en ucuza' : 'Marka fark etmeksizin, her ürünün en ucuzu'}</Text>
                <Text style={{ color: onCard, fontSize: 38, fontWeight: '800', letterSpacing: -1 }}>{plan ? `${formatTL(num(plan.total))} ₺` : '—'}</Text>
                {mode === 'nearby' && plan && (
                  <Text style={{ color: onCard, fontSize: 13, marginTop: 2 }}>{"Başka bir markette ürün başına 1 ₺'den fazla ucuzsa orada alınır."}</Text>
                )}
                {mode === 'opportunist' && opt.nearby && num(opt.nearby_extra) > 0 && (
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: 'rgba(255,255,255,0.2)', alignSelf: 'flex-start', borderRadius: 10, paddingHorizontal: 10, paddingVertical: 6, marginTop: 4 }}>
                    <Icon name="trending-up" size={16} color={onCard} />
                    <Text style={{ color: onCard, fontWeight: '700', fontSize: 14 }}>En yakın market planına göre {formatTL(num(opt.nearby_extra))} ₺ daha ucuz</Text>
                  </View>
                )}
                {mode === 'opportunist' && num(opt.savings.weekly) > 0 && (
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: 'rgba(255,255,255,0.2)', alignSelf: 'flex-start', borderRadius: 10, paddingHorizontal: 10, paddingVertical: 6, marginTop: 4 }}>
                    <Icon name="trending-up" size={16} color={onCard} />
                    <Text style={{ color: onCard, fontWeight: '700', fontSize: 14 }}>Seçimlerinize göre {formatTL(num(opt.savings.weekly))} ₺ daha ucuz (yılda ~{formatTL(num(opt.savings.yearly), 0)} ₺)</Text>
                  </View>
                )}
              </View>}
              {mode === 'nearby' && !opt.nearby && (
                <Card style={{ gap: 10 }}>
                  <Text style={{ color: t.text, fontWeight: '800' }}>
                    {loc === 'asking' || loc === 'idle' ? 'Konumunuz alınıyor…'
                      : loc === 'denied' ? 'Konum izni kapalı'
                      : loc === 'outside' ? 'Konumunuz Türkiye dışında görünüyor'
                      : loc === 'unavailable' ? 'Konum alınamadı'
                      : 'Yakınınızda market bulunamadı'}
                  </Text>
                  <Muted>
                    {loc === 'ready'
                      ? 'Profil sayfanızdan "çevremdeki marketler"i seçin; En yakın market planı seçtiğiniz şubelerin mesafesine göre hazırlanır.'
                      : 'En yakın market planı, size en yakın marketten başlamak için konumunuzu kullanır. Konumunuz kaydedilmez.'}
                  </Muted>
                  {loc === 'asking' || loc === 'idle' ? <ActivityIndicator color={t.tint} /> : loc !== 'ready' && (
                    <Button title={loc === 'denied' ? 'Ayarlardan izin ver' : 'Tekrar dene'}
                      onPress={() => (loc === 'denied' && Platform.OS !== 'web' ? Linking.openSettings() : askLocation())} />
                  )}
                </Card>
              )}
              {mode === 'single_market' && !opt.single_market.available && (
                <Text style={{ color: t.accentText, backgroundColor: t.accentSoft, borderRadius: 14, padding: 12 }}>{opt.single_market.warning || 'Hiçbir market listedeki tüm ürünleri satmıyor.'}</Text>
              )}
              {plan?.by_market.map(b => (
                <Card key={b.market_id} style={{ gap: 4, padding: 14 }}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <MarketBadge id={b.market_id} size={26} />
                    <Text style={{ color: t.text, fontWeight: '800', fontSize: 16, flex: 1 }}>{marketById(b.market_id)?.name}</Text>
                    <Text style={{ color: t.text, fontWeight: '800', fontSize: 17 }}>{formatTL(num(b.total))} ₺</Text>
                  </View>
                  {storeInfo(plan.lines.filter(l => b.item_ids.includes(l.item_id) && l.store_id != null).map(l => l.store_id as number))}
                  {plan.lines.filter(l => b.item_ids.includes(l.item_id)).map(l => (
                    <View key={l.item_id} style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 8, borderTopWidth: 1, borderTopColor: t.border, paddingVertical: 8 }}>
                      <Muted style={{ flex: 1 }}>{l.group_name} ({l.substituted ? l.product_name : l.brand || l.product_name}){l.substituted ? ' · benzeri alındı' : ''}</Muted>
                      <Text style={{ color: t.text, fontWeight: '700', fontSize: 14 }}>{formatTL(num(l.line_total))} ₺</Text>
                    </View>
                  ))}
                </Card>
              ))}
              {mode === 'single_market' && (
                <Card style={{ gap: 2, padding: 14 }}>
                  <Muted style={{ fontWeight: '700' }}>MARKETLERE GÖRE</Muted>
                  {opt.single_market.markets.filter(m => m.found > 0).map(m => (
                    <Muted key={m.market_id} style={{ paddingVertical: 3 }}>
                      {marketById(m.market_id)?.name}: {formatTL(num(m.total))} ₺{m.substituted ? ` · ${m.substituted} farklı marka` : ''}{m.missing ? ` · ${m.missing} ürün yok` : ''}
                    </Muted>
                  ))}
                </Card>
              )}
            </>
          )}
        </>
      )}
      <ItemPicker item={pickItem ? (itemById.get(pickItem.id) ?? null) : null} onClose={() => setPickItem(null)}
        onPick={patch => { const id = pickItem?.id; setPickItem(null); if (id != null) void update(id, patch); }} />
    </Screen>
  );
}
