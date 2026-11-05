import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';

import Icon from '@/components/Icon';
import MarketBadge from '@/components/MarketBadge';
import ProductImage from '@/components/ProductImage';
import { ActionBar, Button, Card, Muted, Screen, useTheme } from '@/components/ui';
import { api, DealIngredient, num } from '@/lib/api';
import { formatTL } from '@/lib/format';

/**
 * İndirimden menü: şu an indirimdeki tarif malzemeleri (fırsatlar + aktüel). Seçilen malzemeyi kullanan
 * tarifler haftalık planda öne çıkar ("tavuk indirimde, tavuklu hafta"). Gerçek indirimliler (en fazla 8) seçili gelir; kapatılabilir.
 */
export default function DealMenuScreen() {
  const t = useTheme();
  const [items, setItems] = useState<DealIngredient[] | null>(null);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.dealIngredients()
      .then(d => { setItems(d); setPicked(new Set(d.filter(i => i.discount_percent > 0).slice(0, 8).map(i => i.name))); })
      .catch(e => { setItems([]); setError((e as Error).message); });
  }, []);

  const toggle = (name: string) => setPicked(prev => {
    const next = new Set(prev);
    if (next.has(name)) next.delete(name); else next.add(name);
    return next;
  });

  const create = async () => {
    setBusy(true);
    setError(null);
    try {
      const plan = await api.createMealPlan({
        period: 'weekly', servings: 2, meal_slots: ['aksam'], courses: ['corba', 'ana', 'yan', 'salata'],
        prefer: Array.from(picked), name: 'İndirimden menü',
      });
      router.replace({ pathname: '/meals/[id]', params: { id: String(plan.id) } });
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <Screen safeTop={false} footer={items !== null && (
      <ActionBar>
        {error && <Text style={{ color: t.danger }}>{error}</Text>}
        <Button title={picked.size ? `${picked.size} malzemeyle haftalık menü kur` : 'Haftalık menü kur'} onPress={create} busy={busy} />
      </ActionBar>
    )}>
      <Text style={{ color: t.text, fontSize: 22, fontWeight: '800' }}>İndirimden menü</Text>
      <Muted>Bu hafta indirimde olan malzemeleri seçin; menüde o malzemeli yemekler öne çıksın. Fiyatlar yine marketlerdeki güncel fiyattan hesaplanır.</Muted>
      {items === null && <ActivityIndicator color={t.tint} style={{ marginTop: 24 }} />}
      {items?.length === 0 && !error && (
        <Card><Muted>Şu an tariflerde kullanılan indirimli malzeme bulunamadı. Normal planı kurabilirsiniz.</Muted></Card>
      )}
      {items?.map((i, idx) => {
        const real = i.discount_percent > 0;
        const header = idx === 0 || real !== (items[idx - 1].discount_percent > 0)
          ? (real ? 'GERÇEK İNDİRİM · en çok tasarruf üstte' : 'BROŞÜRDE · indirim oranı bilinmiyor') : null;
        const on = picked.has(i.name);
        return (
          <View key={i.name} style={{ gap: 8 }}>
          {header && <Text style={{ color: t.textMuted, fontSize: 13, fontWeight: '800', marginTop: 8 }}>{header}</Text>}
          <Pressable onPress={() => toggle(i.name)} accessibilityRole="checkbox" accessibilityState={{ checked: on }}
            style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, borderRadius: 14, borderWidth: 1,
              borderColor: on ? t.tint : t.border, backgroundColor: on ? t.tint + '18' : t.card }}>
            <ProductImage uri={i.image_url} icon="tag" size={48} />
            <View style={{ flex: 1, gap: 2 }}>
              <Text style={{ color: t.text, fontWeight: '700' }}>{i.name}</Text>
              <Muted>{i.product_name} · {i.recipe_count} tarif{i.recipe_names?.length ? `: ${i.recipe_names.join(', ')}${i.recipe_count > i.recipe_names.length ? '…' : ''}` : ''}</Muted>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                {i.market_id != null && <MarketBadge id={i.market_id} size={18} />}
                {i.market_slug && <MarketBadge slug={i.market_slug} size={18} />}
                <Text style={{ color: t.tint, fontWeight: '800' }}>{formatTL(num(i.price))} ₺</Text>
                {i.previous_price && num(i.previous_price) > num(i.price) && (
                  <Text style={{ color: t.textMuted, fontSize: 13, textDecorationLine: 'line-through' }}>{formatTL(num(i.previous_price))} ₺</Text>
                )}
                {i.discount_percent > 0 && <Text style={{ color: '#c2410c', fontSize: 13, fontWeight: '800' }}>%{i.discount_percent}</Text>}
              </View>
            </View>
            <Icon name={on ? 'check-square' : 'square'} size={24} color={on ? t.tint : t.textMuted} />
          </Pressable>
          </View>
        );
      })}
      {items?.length === 0 && error && <Text style={{ color: t.danger }}>{error}</Text>}
    </Screen>
  );
}
