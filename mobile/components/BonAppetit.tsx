import * as Haptics from 'expo-haptics';
import { useEffect, useRef, useState } from 'react';
import { AccessibilityInfo, Animated, Dimensions, Easing, Modal, Pressable, Text, View } from 'react-native';

import FoodIcon from '@/components/FoodIcon';

const DURATION_MS = 3500; // ekran bu kadar kalır (ya da dokununca kapanır), sonra onDone
const PIECES = ['✨', '🍽️', '⭐', '🥄', '✨', '🍴'];

function Spark({ glyph, delay, x }: { glyph: string; delay: number; x: number }) {
  const [rise] = useState(() => new Animated.Value(0));
  useEffect(() => {
    Animated.timing(rise, { toValue: 1, duration: 2400, delay, easing: Easing.out(Easing.quad), useNativeDriver: true }).start();
  }, [rise, delay]);
  const height = Dimensions.get('window').height;
  return (
    <Animated.Text style={{
      position: 'absolute', bottom: -30, left: x, fontSize: 26,
      opacity: rise.interpolate({ inputRange: [0, 0.2, 0.8, 1], outputRange: [0, 1, 1, 0] }),
      transform: [{ translateY: rise.interpolate({ inputRange: [0, 1], outputRange: [0, -(height * 0.9)] }) }],
    }}>{glyph}</Animated.Text>
  );
}

/** Pişirme bitince tam ekran "Afiyet olsun!" kartı; birkaç saniye sonra ya da dokununca onDone */
export default function BonAppetit({ dish, onDone }: { dish: string; onDone: () => void }) {
  const [pop] = useState(() => new Animated.Value(0));
  const [reduced, setReduced] = useState(false);
  const done = useRef(onDone);
  useEffect(() => { done.current = onDone; }, [onDone]);
  const width = Dimensions.get('window').width;

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduced).catch(() => {});
    Animated.spring(pop, { toValue: 1, friction: 5, useNativeDriver: true }).start();
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    const timer = setTimeout(() => done.current(), DURATION_MS);
    return () => clearTimeout(timer);
  }, [pop]);

  return (
    <Modal visible animationType="fade" statusBarTranslucent onRequestClose={() => done.current()}>
      <Pressable onPress={() => done.current()} style={{ flex: 1, backgroundColor: '#047857', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        {!reduced && PIECES.map((g, i) => <Spark key={i} glyph={g} delay={i * 220} x={((i * 53) % 100) / 100 * (width - 40)} />)}
        <Animated.View style={{ alignItems: 'center', gap: 10, transform: [{ scale: pop.interpolate({ inputRange: [0, 1], outputRange: [0.6, 1] }) }] }}>
          <View style={{ width: 124, height: 124, borderRadius: 62, backgroundColor: 'rgba(255,255,255,0.18)', alignItems: 'center', justifyContent: 'center' }}>
            <FoodIcon name="silverware-fork-knife" size={68} color="#fff" />
          </View>
          <Text style={{ color: '#fff', fontSize: 44, fontWeight: '900', letterSpacing: -1, marginTop: 8 }}>Afiyet olsun!</Text>
          <Text style={{ color: '#fff', opacity: 0.9, fontSize: 17, textAlign: 'center' }}>{dish} hazır. Elinize sağlık.</Text>
        </Animated.View>
      </Pressable>
    </Modal>
  );
}
