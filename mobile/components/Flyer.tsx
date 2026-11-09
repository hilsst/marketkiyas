import { useEffect, useRef, useState } from 'react';
import { Animated, Modal, View } from 'react-native';
import { Text } from './Text';
import { useTheme } from '@/components/ui';
import Icon from '@/components/Icon';

/** Kısa süreli onay kartı ("Listeye eklendi"): ortada belirir, `durationMs` sonra onDone */
export default function Flyer({ title, subtitle, durationMs = 1300, onDone }: {
  title: string; subtitle?: string; durationMs?: number; onDone: () => void;
}) {
  const t = useTheme();
  const [scale] = useState(() => new Animated.Value(0.7));
  const done = useRef(onDone);
  useEffect(() => { done.current = onDone; }, [onDone]);

  useEffect(() => {
    Animated.spring(scale, { toValue: 1, friction: 5, useNativeDriver: true }).start();
    const timer = setTimeout(() => done.current(), durationMs);
    return () => clearTimeout(timer);
  }, [scale, durationMs]);

  return (
    <Modal visible transparent animationType="fade">
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(0,0,0,0.25)' }}>
        <Animated.View style={{ transform: [{ scale }], backgroundColor: t.celebrate, borderRadius: 24, paddingVertical: 26, paddingHorizontal: 34, alignItems: 'center', gap: 6 }}>
          <Icon name="check-circle" size={52} color="#fff" />
          <Text style={{ color: '#fff', fontSize: 20, fontWeight: '800' }}>{title}</Text>
          {subtitle && <Text style={{ color: '#fff', textAlign: 'center' }}>{subtitle}</Text>}
        </Animated.View>
      </View>
    </Modal>
  );
}
