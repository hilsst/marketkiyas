import { Modal, Pressable, ScrollView, View } from 'react-native';
import { Text } from './Text';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import FoodIcon from '@/components/FoodIcon';
import Icon from '@/components/Icon';
import { Button, Muted, useTheme } from '@/components/ui';
import { formatSize, MealPlanExport } from '@/lib/api';
import type { FoodGlyph } from '@/lib/icons';

/** Kilere kaydedilen malzemenin adından vektör simge (eşleşme yoksa paket simgesi) */
const KEYWORDS: [RegExp, FoodGlyph][] = [
  [/un\b|bulgur|pirinç|makarna|nişasta|irmik|mercimek|nohut|fasulye/i, 'grain'],
  [/ekmek|pide|lavaş|yufka/i, 'baguette'],
  [/dana|kuzu|kıyma|kuşbaşı|tavuk|et\b|balık|sucuk/i, 'food-drumstick'],
  [/domates|salça|biber|patlıcan|soğan|sarımsak|salatalık|havuç|patates|sebze/i, 'food-apple'],
  [/süt|yoğurt|peynir|tereyağı|yağ\b|yumurta|ayran|krema/i, 'cow'],
  [/şeker|bal\b|reçel|çikolata|bisküvi/i, 'cookie'],
  [/çay|kahve|su\b|meyve suyu/i, 'cup'],
];
const glyphFor = (name: string): FoodGlyph => KEYWORDS.find(([re]) => re.test(name))?.[1] ?? 'package-variant-closed';

/**
 * Plan -> liste aktarımı bitince gösterilen başarı alt sayfası: eklenen ürün sayısı, kilere kaydedilen
 * artanlar ve eklenemeyen ürünler. "Listeyi aç" birincil, "Planda kal" ikincil eylemdir.
 */
export default function ExportSuccessSheet({ result, onOpen, onClose }: {
  result: MealPlanExport | null; onOpen: () => void; onClose: () => void;
}) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const stored = result?.stored ?? [];
  const skipped = result?.skipped ?? [];
  return (
    <Modal visible={!!result} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(15,31,25,0.5)' }} onPress={onClose} accessibilityLabel="Kapat" />
      {result && (
        <View style={{ backgroundColor: t.card, borderTopLeftRadius: 28, borderTopRightRadius: 28, paddingTop: 10, paddingHorizontal: 20,
          paddingBottom: 16 + insets.bottom, maxHeight: '88%' }}>
          <View style={{ alignSelf: 'center', width: 40, height: 4, borderRadius: 2, backgroundColor: t.border, marginBottom: 16 }} />
          <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ gap: 12 }}>
            <View style={{ alignItems: 'center', gap: 4 }}>
              <View style={{ width: 68, height: 68, borderRadius: 34, backgroundColor: t.tintSoft, alignItems: 'center', justifyContent: 'center', marginBottom: 6 }}>
                <View style={{ width: 48, height: 48, borderRadius: 24, backgroundColor: t.tint, alignItems: 'center', justifyContent: 'center' }}>
                  <Icon name="check" size={28} color="#fff" />
                </View>
              </View>
              <Text style={{ color: t.text, fontSize: 22, fontWeight: '800' }}>Listene eklendi</Text>
              <Muted style={{ textAlign: 'center' }}>Plandaki malzemeler en uygun paketlerle hazır.</Muted>
            </View>

            <View style={{ flexDirection: 'row', gap: 10 }}>
              <Stat n={result.added} label="ürün eklendi" />
              {stored.length > 0 && <Stat n={stored.length} label="artan kilere girdi" />}
            </View>

            {stored.length > 0 && (
              <View style={{ backgroundColor: t.tintSoft, borderRadius: 18, padding: 14, gap: 10 }}>
                <View style={{ gap: 2 }}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                    <Icon name="package" size={20} color={t.tintDark} />
                    <Text style={{ color: t.tintDark, fontWeight: '800', fontSize: 15 }}>Kilerine kaydedildi</Text>
                  </View>
                  <Muted>Sonraki planlar önce bunları kullanır.</Muted>
                </View>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                  {stored.map((s, i) => (
                    <View key={`${s.name}-${i}`} style={{ flexBasis: '48%', flexGrow: 1, backgroundColor: t.card, borderRadius: 14, padding: 10,
                      flexDirection: 'row', alignItems: 'center', gap: 9 }}>
                      <View style={{ width: 34, height: 34, borderRadius: 10, backgroundColor: t.tintSoft, alignItems: 'center', justifyContent: 'center' }}>
                        <FoodIcon name={glyphFor(s.name)} size={19} />
                      </View>
                      <View style={{ flex: 1 }}>
                        <Text style={{ color: t.text, fontWeight: '700', fontSize: 14 }}>{s.name}</Text>
                        <Text style={{ color: t.tintDark, fontWeight: '800', fontSize: 14 }}>{formatSize(s.quantity, s.unit)}</Text>
                      </View>
                    </View>
                  ))}
                </View>
              </View>
            )}

            {skipped.length > 0 && (
              <View style={{ backgroundColor: t.accentSoft, borderRadius: 14, padding: 12, flexDirection: 'row', gap: 9, alignItems: 'flex-start' }}>
                <Icon name="alert-triangle" size={18} color={t.accentText} />
                <Text style={{ flex: 1, color: t.accentText, fontWeight: '600', fontSize: 14 }}>
                  Marketlerinizde bulunamadığı için eklenmedi: {skipped.join(', ')}
                </Text>
              </View>
            )}

            <View style={{ gap: 10, marginTop: 4 }}>
              <Button title="Listeyi aç" onPress={onOpen} />
              <Button title="Planda kal" kind="secondary" onPress={onClose} />
            </View>
          </ScrollView>
        </View>
      )}
    </Modal>
  );
}

function Stat({ n, label }: { n: number; label: string }) {
  const t = useTheme();
  return (
    <View style={{ flex: 1, backgroundColor: t.background, borderRadius: 16, paddingVertical: 12, alignItems: 'center' }}>
      <Text style={{ color: t.tintDark, fontSize: 24, fontWeight: '800' }}>{n}</Text>
      <Muted style={{ fontSize: 13 }}>{label}</Muted>
    </View>
  );
}
