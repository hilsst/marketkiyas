import { Text, View } from 'react-native';

import MarketBadge from '@/components/MarketBadge';
import { Card, Muted, useTheme } from '@/components/ui';
import { formatSize, MealCost, num } from '@/lib/api';

const tl = (v: string | number | null) => `${num(v).toFixed(2)} ₺`;

/** Plan / tarif maliyeti: özet ve her malzeme için seçilen en uygun ürün */
export default function MealCostCard({ cost, title = 'Malzeme maliyeti' }: { cost: MealCost; title?: string }) {
  const t = useTheme();
  return (
    <Card style={{ gap: 12 }}>
      <Text style={{ color: t.text, fontWeight: '800', fontSize: 17 }}>{title}</Text>
      <View style={{ flexDirection: 'row', gap: 10 }}>
        <View style={{ flex: 1, backgroundColor: t.tint, borderRadius: 14, padding: 12, gap: 2 }}>
          <Text style={{ color: '#fff', fontSize: 11, fontWeight: '700' }}>ALIŞVERİŞ TUTARI</Text>
          <Text style={{ color: '#fff', fontSize: 24, fontWeight: '900' }}>{tl(cost.purchase_total)}</Text>
        </View>
        <View style={{ flex: 1, borderRadius: 14, padding: 12, gap: 2, borderWidth: 1, borderColor: t.border }}>
          <Text style={{ color: t.textMuted, fontSize: 11, fontWeight: '700' }}>KİŞİ BAŞI ÖĞÜN</Text>
          <Text style={{ color: t.text, fontSize: 24, fontWeight: '900' }}>{cost.per_serving ? tl(cost.per_serving) : '—'}</Text>
        </View>
      </View>
      <Muted>
        Yemeklerde kullanılan kısmın değeri {tl(cost.used_total)} ({cost.portions} porsiyon). Alışveriş tutarı paket
        hâlinde alınacakların toplamıdır; artan malzeme evde kalır.
      </Muted>
      {num(cost.leftover_value ?? 0) > 0 && (
        <Muted>🧩 Paketlerden artacak malzemenin değeri yaklaşık {tl(cost.leftover_value ?? 0)}.</Muted>
      )}
      {cost.missing_count > 0 && (
        <Text style={{ color: t.danger, fontSize: 13 }}>
          {cost.missing_count} malzemenin fiyatı marketlerinizde bulunamadı; toplama eklenmedi.
        </Text>
      )}

      {cost.lines.map((line, i) => (
        <View key={`${line.name}-${line.unit}-${i}`} style={{ flexDirection: 'row', gap: 10, alignItems: 'center', borderTopWidth: 1, borderTopColor: t.border, paddingTop: 10 }}>
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

      {(cost.have?.length ?? 0) > 0 && (
        <Muted>🧺 Dolabınızda olduğu için alınmayacak: {cost.have!.join(', ')}</Muted>
      )}
      {cost.pantry.length > 0 && (
        <Muted>Evde olduğu varsayılanlar: {cost.pantry.join(', ')}</Muted>
      )}
    </Card>
  );
}
