import { setAudioModeAsync, useAudioPlayer } from 'expo-audio';
import * as Haptics from 'expo-haptics';
import { useEffect, useMemo, useRef, useState } from 'react';
import { AccessibilityInfo, Animated, Dimensions, Easing, Modal, Pressable, Text, View } from 'react-native';

const DURATION_MS = 4000; // kutlama ekranı bu kadar kalır, sonra onDone
const CALM_DURATION_MS = 2500; // kazanç yoksa sakin ekran
const PIECES = ['🎉', '✨', '🎊', '💰', '🪙', '⭐'];

/** Yukarıdan dökülen konfeti/para parçası */
function Piece({ glyph, delay, x }: { glyph: string; delay: number; x: number }) {
  const [fall] = useState(() => new Animated.Value(0));
  useEffect(() => {
    Animated.timing(fall, { toValue: 1, duration: 2600, delay, easing: Easing.in(Easing.quad), useNativeDriver: true }).start();
  }, [fall, delay]);
  const height = Dimensions.get('window').height;
  return (
    <Animated.Text style={{
      position: 'absolute', top: -40, left: x, fontSize: 28,
      transform: [
        { translateY: fall.interpolate({ inputRange: [0, 1], outputRange: [0, height + 80] }) },
        { rotate: fall.interpolate({ inputRange: [0, 1], outputRange: ['0deg', `${delay % 2 ? 360 : -360}deg`] }) },
      ],
    }}>{glyph}</Animated.Text>
  );
}

/**
 * "Alışverişi Bitir" sonrası tam ekran kutlama (web'deki components/Celebration.tsx'in telefon hâli): kasaya
 * eklenen ya da bu alışverişte ortalama fiyatlara göre kazanılan tutar, dökülen konfeti, bozuk para sesi ve titreşim.
 * 4 saniye sonra (ya da dokununca) onDone. Kazanç yoksa sakin özet; "hareketi azalt" açıksa konfeti yok.
 */
export default function Celebration({ savedAmount, shoppingSavings, vaultTotal, note, onDone }: {
  savedAmount: number; shoppingSavings: number; vaultTotal: number; note: string | null; onDone: () => void;
}) {
  const amount = savedAmount > 0 ? savedAmount : shoppingSavings;
  const festive = amount > 0;
  const player = useAudioPlayer(require('@/assets/sounds/coin.wav'));
  const done = useRef(onDone);
  useEffect(() => { done.current = onDone; }, [onDone]);
  const [reduced, setReduced] = useState(false);
  const [pop] = useState(() => new Animated.Value(0));
  const width = Dimensions.get('window').width;
  const pieces = useMemo(
    () => Array.from({ length: 28 }, (_, i) => ({ glyph: PIECES[i % PIECES.length], delay: (i * 97) % 1400, x: ((i * 137) % 100) / 100 * (width - 30) })),
    [width],
  );

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduced).catch(() => {});
    Animated.spring(pop, { toValue: 1, friction: 5, useNativeDriver: true }).start();
    if (festive) {
      setAudioModeAsync({ playsInSilentMode: false }).catch(() => {});
      try { player.play(); } catch { /* ses çalınamazsa kutlama yine sürer */ }
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    }
    const timer = setTimeout(() => done.current(), festive ? DURATION_MS : CALM_DURATION_MS);
    return () => clearTimeout(timer);
  }, [festive, player, pop]);

  return (
    <Modal visible animationType="fade" onRequestClose={() => done.current()}>
      <Pressable onPress={() => done.current()} style={{ flex: 1, backgroundColor: festive ? '#047857' : '#111827', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        {festive && !reduced && pieces.map((p, i) => <Piece key={i} {...p} />)}
        <Animated.View style={{ alignItems: 'center', transform: [{ scale: pop.interpolate({ inputRange: [0, 1], outputRange: [0.6, 1] }) }] }}>
          {festive ? (
            <>
              <Text style={{ fontSize: 72 }}>💰</Text>
              <Text style={{ color: '#fff', fontSize: 18, fontWeight: '600', opacity: 0.9, marginTop: 8 }}>
                {savedAmount > 0 ? 'Tebrikler! Tasarruf kasana eklendi' : 'Tebrikler! Bu alışverişte kazancın'}
              </Text>
              <Text style={{ color: '#fff', fontSize: 56, fontWeight: '900', marginVertical: 6 }}>{amount.toFixed(2)} ₺</Text>
              {savedAmount <= 0 && <Text style={{ color: '#fff', opacity: 0.85, fontSize: 12 }}>ortalama raf fiyatlarına göre</Text>}
              <Text style={{ color: '#fff', opacity: 0.9, marginTop: 6 }}>Kasandaki toplam: {vaultTotal.toFixed(2)} ₺</Text>
              <Text style={{ color: '#fff', opacity: 0.75, fontSize: 12, marginTop: 4 }}>Bu tempoyla yılda yaklaşık {(amount * 52).toFixed(0)} ₺</Text>
            </>
          ) : (
            <>
              <Text style={{ fontSize: 64 }}>✅</Text>
              <Text style={{ color: '#fff', fontSize: 24, fontWeight: '800', marginTop: 8 }}>Alışveriş tamamlandı</Text>
            </>
          )}
          {note && <Text style={{ color: '#fff', opacity: 0.75, fontSize: 12, marginTop: 10, textAlign: 'center' }}>{note}</Text>}
          <View style={{ height: 24 }} />
          <Text style={{ color: '#fff', opacity: 0.6, fontSize: 11 }}>Ana sayfaya dönülüyor…</Text>
        </Animated.View>
      </Pressable>
    </Modal>
  );
}
