import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import Icon from '@/components/Icon';
import MarketBadge from '@/components/MarketBadge';
import { Card, Muted, useTheme } from '@/components/ui';
import { formatSize, MealCost, num } from '@/lib/api';

const tl = (v: string | number | null) => `${num(v).toFixed(2)} ₺`;
const CHIPS_SHOWN = 10;

/** Plan / tarif maliyeti: rakamlar, kısa özet, açılır "dolabından" bölümü ve alınacak ürünler */
export default function MealCostCard({ cost, title = 'Malzeme maliyeti' }: { cost: MealCost; title?: string }) {
  const t = useTheme();
  const [open, setOpen] = useState(false);
  const [allChips, setAllChips] = useState(false);

  const stock = cost.from_stock ?? [];
  const have = cost.have ?? [];
  const leftover = num(cost.leftover_value ?? 0);
  const homeCount = stock.length + have.length + cost.pantry.length;

  const chip = (key: string, name: string, amount?: string) => (
    <View key={key} style={{ backgroundColor: t.card, borderWidth: 1, borderColor: t.border, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 5 }}>
      <Text style={{ color: t.text, fontSize: 12 }}>{name}{amount ? <Text style={{ color: t.textMuted }}> {amount}</Text> : null}</Text>
    </View>
  );
  const shownStock = allChips ? stock : stock.slice(0, CHIPS_SHOWN);

  const row = (label: string, value: string) => (
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 10 }}>
      <Text style={{ color: t.textMuted, fontSize: 14, flex: 1 }}>{label}</Text>
      <Text style={{ color: t.text, fontSize: 14, fontWeight: '700' }}>{value}</Text>
    </View>
  );

  return (
    <Card style={{ gap: 12 }}>
      <Text style={{ color: t.text, fontWeight: '800', fontSize: 18, letterSpacing: -0.3 }}>{title}</Text>
      <View style={{ flexDirection: 'row', gap: 10 }}>
        <View style={{ flex: 1, backgroundColor: t.tint, borderRadius: 18, padding: 14, gap: 2 }}>
          <Text style={{ color: '#fff', fontSize: 11, fontWeight: '700' }}>ALIŞVERİŞ TUTARI</Text>
          <Text style={{ color: '#fff', fontSize: 26, fontWeight: '800', letterSpacing: -0.5 }}>{tl(cost.purchase_total)}</Text>
        </View>
        <View style={{ flex: 1, borderRadius: 18, padding: 14, gap: 2, backgroundColor: t.background }}>
          <Text style={{ color: t.textMuted, fontSize: 11, fontWeight: '700' }}>KİŞİ BAŞI ÖĞÜN</Text>
          <Text style={{ color: t.text, fontSize: 26, fontWeight: '800', letterSpacing: -0.5 }}>{cost.per_serving ? tl(cost.per_serving) : '—'}</Text>
        </View>
      </View>

      <View style={{ gap: 6 }}>
        {row(`Yemeklerde kullanılan · ${cost.portions} porsiyon`, tl(cost.used_total))}
        {leftover > 0 && row('Paketlerden artan (evde kalır)', `~${tl(leftover)}`)}
      </View>

      {homeCount > 0 && (
        <>
          <Pressable onPress={() => setOpen(o => !o)} accessibilityRole="button" accessibilityState={{ expanded: open }}
            style={{ flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: t.tintSoft, borderRadius: 14, paddingHorizontal: 12, paddingVertical: 11 }}>
            <Icon name="package" size={18} color={t.tintDark} />
            <Text style={{ color: t.tintDark, fontWeight: '700', fontSize: 14, flex: 1 }}>Dolabından kullanılanlar</Text>
            <View style={{ backgroundColor: t.card, borderRadius: 999, paddingHorizontal: 9, paddingVertical: 1 }}>
              <Text style={{ color: t.tintDark, fontSize: 12, fontWeight: '700' }}>{homeCount}</Text>
            </View>
            <Icon name={open ? 'chevron-up' : 'chevron-down'} size={18} color={t.tintDark} />
          </Pressable>
          {open && (
            <View style={{ gap: 10 }}>
              {stock.length > 0 && (
                <View style={{ gap: 6 }}>
                  <Muted style={{ fontSize: 12 }}>Önceki alışverişten artan</Muted>
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
                    {shownStock.map((s, i) => chip(`s${i}`, s.name, formatSize(s.quantity, s.unit)))}
                    {!allChips && stock.length > CHIPS_SHOWN && (
                      <Pressable onPress={() => setAllChips(true)}
                        style={{ backgroundColor: t.card, borderWidth: 1, borderColor: t.border, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 5 }}>
                        <Text style={{ color: t.tint, fontSize: 12, fontWeight: '700' }}>+ {stock.length - CHIPS_SHOWN} tane daha</Text>
                      </Pressable>
                    )}
                  </View>
                </View>
              )}
              {have.length > 0 && (
                <View style={{ gap: 6 }}>
                  <Muted style={{ fontSize: 12 }}>Dolabında olduğu için alınmayacak</Muted>
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>{have.map((h, i) => chip(`h${i}`, h))}</View>
                </View>
              )}
              {cost.pantry.length > 0 && (
                <View style={{ gap: 6 }}>
                  <Muted style={{ fontSize: 12 }}>Evde olduğu varsayılanlar</Muted>
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>{cost.pantry.map((p, i) => chip(`p${i}`, p))}</View>
                </View>
              )}
            </View>
          )}
        </>
      )}

      {cost.missing_count > 0 && (
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: t.accentSoft, borderRadius: 12, paddingHorizontal: 12, paddingVertical: 9 }}>
          <Icon name="alert-triangle" size={16} color={t.accentText} />
          <Text style={{ color: t.accentText, fontSize: 13, fontWeight: '600', flex: 1 }}>
            {cost.missing_count} malzemenin fiyatı bulunamadı, toplama eklenmedi
          </Text>
        </View>
      )}

      {cost.lines.length > 0 && (
        <Text style={{ color: t.textMuted, fontSize: 12, fontWeight: '800', letterSpacing: 0.4, marginBottom: -4 }}>ALINACAKLAR</Text>
      )}
      {cost.lines.map((line, i) => (
        <View key={`${line.name}-${line.unit}-${i}`}
          style={{ flexDirection: 'row', gap: 10, alignItems: 'center', borderTopWidth: i === 0 ? 0 : 1, borderTopColor: t.border, paddingTop: i === 0 ? 0 : 10 }}>
          <View style={{ flex: 1, gap: 2 }}>
            <Text style={{ color: t.text, fontWeight: '600' }}>
              {line.name} <Text style={{ color: t.textMuted, fontWeight: '400' }}>· {formatSize(line.needed_quantity, line.unit)}</Text>
            </Text>
            {line.match ? (
              <Muted>
                {line.packages} × {line.match.name}{line.approximate ? ' (yaklaşık)' : ''} · {tl(line.match.price)}
              </Muted>
            ) : (
              <Text style={{ color: t.danger, fontSize: 13 }}>Marketlerinizde bulunamadı</Text>
            )}
          </View>
          {line.match?.market_id != null && <MarketBadge id={line.match.market_id} size={22} />}
          <Text style={{ color: t.text, fontWeight: '700', minWidth: 72, textAlign: 'right' }}>
            {line.purchase_cost != null ? tl(line.purchase_cost) : '—'}
          </Text>
        </View>
      ))}
      <Text style={{ color: t.textMuted, fontSize: 12 }}>Alışveriş tutarı, paket fiyatlarının toplamıdır.</Text>
    </Card>
  );
}
