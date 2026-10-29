import { useEffect, useRef, useState } from 'react';
import { Animated, Modal, Text, View } from 'react-native';

/** Kısa süreli onay kartı ("Listeye eklendi ✓"): ortada belirir, `durationMs` sonra onDone */
export default function Flyer({ title, subtitle, durationMs = 1300, onDone }: {
  title: string; subtitle?: string; durationMs?: number; onDone: () => void;
}) {
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
        <Animated.View style={{ transform: [{ scale }], backgroundColor: '#059669', borderRadius: 24, paddingVertical: 26, paddingHorizontal: 34, alignItems: 'center', gap: 6 }}>
          <Text style={{ fontSize: 48 }}>✅</Text>
          <Text style={{ color: '#fff', fontSize: 20, fontWeight: '800' }}>{title}</Text>
          {subtitle && <Text style={{ color: '#fff', opacity: 0.9, textAlign: 'center' }}>{subtitle}</Text>}
        </Animated.View>
      </View>
    </Modal>
  );
}
