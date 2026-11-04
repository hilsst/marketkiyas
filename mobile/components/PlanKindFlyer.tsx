import { useEffect, useState } from 'react';
import { Animated, Modal, Pressable, Text, View } from 'react-native';

import Icon, { IconName } from '@/components/Icon';
import { Muted, useTheme } from '@/components/ui';

export type PlanKind = 'quick' | 'cuisine' | 'pantry';

/**
 * Karşılamada "Yemek Planı"na basınca ortada açılan kart: nasıl bir plan? Üstte öne çıkan "Hızlı ama lezzetli yemekler"
 * (30-45 dakikada biten, malzemesi marketten alınan yemekler), altında mutfak seçerek kurma ve dolaptakilerle plan.
 */
export default function PlanKindFlyer({ quickCount, onPick, onCancel }: {
  quickCount: number; onPick: (kind: PlanKind) => void; onCancel: () => void;
}) {
  const t = useTheme();
  const [scale] = useState(() => new Animated.Value(0.85));
  useEffect(() => { Animated.spring(scale, { toValue: 1, friction: 6, useNativeDriver: true }).start(); }, [scale]);

  const row = (kind: PlanKind, icon: IconName, title: string, note: string) => (
    <Pressable key={kind} onPress={() => onPick(kind)} accessibilityRole="button"
      style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14, borderRadius: 18, borderWidth: 1.5, borderColor: t.border, backgroundColor: t.card }}>
      <View style={{ width: 46, height: 46, borderRadius: 15, backgroundColor: t.tintSoft, alignItems: 'center', justifyContent: 'center' }}>
        <Icon name={icon} size={24} color={t.tint} />
      </View>
      <View style={{ flex: 1, gap: 2 }}>
        <Text style={{ color: t.text, fontWeight: '800', fontSize: 16 }}>{title}</Text>
        <Muted style={{ fontSize: 13 }}>{note}</Muted>
      </View>
      <Icon name="chevron-right" size={20} color={t.textMuted} />
    </Pressable>
  );

  return (
    <Modal visible transparent animationType="fade" onRequestClose={onCancel}>
      <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 20 }}>
        <Animated.View style={{ transform: [{ scale }], backgroundColor: t.background, borderRadius: 28, padding: 18, gap: 12 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
            <View style={{ flex: 1 }}>
              <Text style={{ color: t.text, fontSize: 22, fontWeight: '800', letterSpacing: -0.4 }}>Nasıl bir plan istersin?</Text>
              <Muted>Hepsinde fiyat gerçek market fiyatı</Muted>
            </View>
            <Pressable onPress={onCancel} accessibilityRole="button" accessibilityLabel="Kapat" hitSlop={12}>
              <Icon name="x" size={24} color={t.textMuted} />
            </Pressable>
          </View>

          <Pressable onPress={() => onPick('quick')} accessibilityRole="button"
            style={{ borderRadius: 22, padding: 16, gap: 10, backgroundColor: t.tint }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
              <View style={{ width: 46, height: 46, borderRadius: 15, backgroundColor: 'rgba(255,255,255,0.2)', alignItems: 'center', justifyContent: 'center' }}>
                <Icon name="clock" size={26} color="#fff" />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={{ color: '#fff', fontSize: 12, fontWeight: '800', letterSpacing: 0.6, opacity: 0.85 }}>HIZLI AMA LEZZETLİ YEMEKLER</Text>
                <Text style={{ color: '#fff', fontSize: 19, fontWeight: '800', letterSpacing: -0.3 }}>Restoran gibi sofra, market fiyatına.</Text>
              </View>
            </View>
            <Text style={{ color: '#fff', fontSize: 14, fontWeight: '600', opacity: 0.95 }}>
              Her malzemesi markette, 45 dakikada sofrada.{quickCount > 0 ? ` ${quickCount} yemek.` : ''}
            </Text>
          </Pressable>

          {row('cuisine', 'globe', 'Mutfak seçerek kur', 'Türk, İtalyan, Uzak Doğu, Meksika')}
          {row('pantry', 'archive', 'Dolabımdakilerle', 'Evdekini önce kullan, eksiği al')}
        </Animated.View>
      </View>
    </Modal>
  );
}
