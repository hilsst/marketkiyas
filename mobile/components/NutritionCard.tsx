import { Text, View } from 'react-native';

import { Card, Muted, useTheme } from '@/components/ui';
import { Nutrition } from '@/lib/api';

/** Kişi başı yaklaşık kalori, protein, karbonhidrat, yağ */
export default function NutritionCard({ nutrition, title, note }: { nutrition: Nutrition; title: string; note?: string }) {
  const t = useTheme();
  const cell = (value: string, label: string) => (
    <View key={label} style={{ flex: 1, alignItems: 'center', gap: 2 }}>
      <Text style={{ color: t.text, fontWeight: '800', fontSize: 18 }}>{value}</Text>
      <Muted style={{ fontSize: 12 }}>{label}</Muted>
    </View>
  );
  return (
    <Card style={{ gap: 10 }}>
      <Text style={{ color: t.text, fontWeight: '800', fontSize: 17 }}>{title}</Text>
      <View style={{ flexDirection: 'row' }}>
        {cell(String(nutrition.kcal), 'kcal')}
        {cell(`${nutrition.protein_g} g`, 'Protein')}
        {cell(`${nutrition.carbs_g} g`, 'Karbonhidrat')}
        {cell(`${nutrition.fat_g} g`, 'Yağ')}
      </View>
      <Muted style={{ fontSize: 12 }}>{note ?? 'Yaklaşık değerlerdir; kullanılan ürüne ve porsiyona göre değişir.'}</Muted>
    </Card>
  );
}
