import { useEffect, useState } from 'react';
import { Animated, Modal, Pressable, ScrollView, Text, View } from 'react-native';

import { Button, Muted, useTheme } from '@/components/ui';
import { Cuisine } from '@/lib/api';

/**
 * "Plan oluştur"a basınca ortada açılan kart: bu hafta (ya da bugün) hangi mutfaklardan yemek
 * olsun? Birden çok mutfak seçilebilir; her öğün bunlardan birinden gelir. Açıkken render edilir.
 */
export default function CuisinePicker({ cuisines, initial, days, busy, error, onCancel, onConfirm }: {
  cuisines: Cuisine[]; initial: string[]; days: number; busy: boolean; error: string | null;
  onCancel: () => void; onConfirm: (slugs: string[]) => void;
}) {
  const t = useTheme();
  const [selected, setSelected] = useState<string[]>(initial);
  const [scale] = useState(() => new Animated.Value(0.85));

  useEffect(() => {
    Animated.spring(scale, { toValue: 1, friction: 6, useNativeDriver: true }).start();
  }, [scale]);

  const toggle = (slug: string) =>
    setSelected(cur => cur.includes(slug) ? cur.filter(s => s !== slug) : [...cur, slug]);
  const when = days === 1 ? 'Bugün' : days === 7 ? 'Bu hafta' : `${days} gün boyunca`;

  return (
    <Modal visible transparent animationType="fade" onRequestClose={onCancel}>
      <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.45)', justifyContent: 'center', padding: 20 }}>
        <Animated.View style={{ transform: [{ scale }], backgroundColor: t.background, borderRadius: 24, maxHeight: '88%', overflow: 'hidden' }}>
          <View style={{ backgroundColor: t.tint, paddingVertical: 18, paddingHorizontal: 20, gap: 4 }}>
            <Text style={{ color: '#fff', fontSize: 22, fontWeight: '800' }}>🌍 {when} hangi mutfaklar?</Text>
            <Text style={{ color: '#fff', opacity: 0.9 }}>
              Bir ya da birkaç mutfak seç. Öğünler bunlara dengeli dağıtılır; her öğün tek mutfaktan gelir.
            </Text>
          </View>

          <ScrollView contentContainerStyle={{ padding: 16, gap: 10 }}>
            {cuisines.map(c => {
              const active = selected.includes(c.slug);
              const empty = c.recipe_count === 0;
              return (
                <Pressable key={c.slug} disabled={empty} onPress={() => toggle(c.slug)} accessibilityRole="checkbox"
                  accessibilityState={{ checked: active, disabled: empty }}
                  style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14, borderRadius: 16, borderWidth: 2,
                    borderColor: active ? t.tint : t.border, backgroundColor: t.card, opacity: empty ? 0.5 : 1 }}>
                  <Text style={{ fontSize: 34 }}>{c.icon ?? '🍽️'}</Text>
                  <View style={{ flex: 1, gap: 2 }}>
                    <Text style={{ color: t.text, fontWeight: '800', fontSize: 16 }}>{c.name}</Text>
                    {empty ? (
                      <Muted style={{ fontSize: 12 }}>Şu an marketlerde malzemesi bulunan tarif yok</Muted>
                    ) : (
                      <Muted style={{ fontSize: 12 }}>
                        {c.recipe_count} tarif{c.examples.length ? ` · ${c.examples.join(', ')}` : ''}
                      </Muted>
                    )}
                  </View>
                  <View style={{ width: 26, height: 26, borderRadius: 13, borderWidth: 2, borderColor: active ? t.tint : t.border,
                    backgroundColor: active ? t.tint : 'transparent', alignItems: 'center', justifyContent: 'center' }}>
                    {active && <Text style={{ color: '#fff', fontWeight: '900' }}>✓</Text>}
                  </View>
                </Pressable>
              );
            })}
            <Muted style={{ fontSize: 12 }}>Malzemelerinden biri uygulamadaki marketlerde bulunmayan tarifler listede yer almaz.</Muted>
            {error && <Text style={{ color: t.danger }}>{error}</Text>}
          </ScrollView>

          <View style={{ flexDirection: 'row', gap: 10, padding: 16, paddingTop: 4 }}>
            <View style={{ flex: 1 }}><Button title="Vazgeç" kind="secondary" onPress={onCancel} /></View>
            <View style={{ flex: 1.4 }}>
              <Button title={selected.length > 1 ? `${selected.length} mutfakla oluştur` : 'Planı oluştur'}
                onPress={() => onConfirm(selected)} busy={busy} disabled={!selected.length} />
            </View>
          </View>
        </Animated.View>
      </View>
    </Modal>
  );
}
