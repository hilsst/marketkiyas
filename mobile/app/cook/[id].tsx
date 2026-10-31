import { useKeepAwake } from 'expo-keep-awake';
import * as Haptics from 'expo-haptics';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, ScrollView, Text, Vibration, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Muted, useTheme } from '@/components/ui';
import { api, RecipeDetail } from '@/lib/api';

/** Adımdaki süreler: "15 dakika", "20-25 dakika" (üst sınır), "1 saat", "10 dk" -> dakika */
export function stepTimers(text: string): number[] {
  const found: number[] = [];
  const re = /(\d+)(?:\s*[-–]\s*(\d+))?\s*(dakika|dk|saat)/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    const value = Number(m[2] ?? m[1]);
    const minutes = m[3].toLowerCase() === 'saat' ? value * 60 : value;
    if (minutes > 0 && minutes <= 600 && !found.includes(minutes)) found.push(minutes);
  }
  return found;
}

interface Timer { id: number; label: string; endsAt: number; done: boolean; }

function newTimer(step: number, minutes: number): Timer {
  const at = Date.now();
  return { id: at, label: `Adım ${step}: ${minutes} dk`, endsAt: at + minutes * 60_000, done: false };
}

const clock = (ms: number) => {
  const s = Math.max(0, Math.ceil(ms / 1000));
  const h = Math.floor(s / 3600);
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, '0');
  const ss = String(s % 60).padStart(2, '0');
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
};

/**
 * Pişirme modu: ekran kapanmaz, her adım tek ekranda büyük yazıyla; adımdaki süre için tek dokunuşla
 * zamanlayıcı (adımlar arasında geçerken de çalışmaya devam eder, bitince titreşir). İlk ekran
 * malzemeleri hazırlama listesidir.
 */
export default function CookScreen() {
  useKeepAwake();
  const t = useTheme();
  const params = useLocalSearchParams<{ id: string; servings?: string }>();
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState(0); // 0 = malzemeler, 1..n = adımlar
  const [ready, setReady] = useState<string[]>([]);
  const [timers, setTimers] = useState<Timer[]>([]);
  const [now, setNow] = useState(() => Date.now());
  const timersRef = useRef<Timer[]>([]);
  useEffect(() => { timersRef.current = timers; }, [timers]);

  useEffect(() => {
    api.recipe(Number(params.id), params.servings ? Number(params.servings) : undefined)
      .then(setRecipe).catch(e => setError((e as Error).message));
  }, [params.id, params.servings]);

  const running = timers.some(x => !x.done);
  useEffect(() => {
    if (!running) return;
    const tick = setInterval(() => {
      const at = Date.now();
      setNow(at);
      const finished = timersRef.current.filter(x => !x.done && x.endsAt <= at);
      if (!finished.length) return;
      setTimers(cur => cur.map(x => finished.some(f => f.id === x.id) ? { ...x, done: true } : x));
      Vibration.vibrate([0, 600, 300, 600, 300, 600]);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
      Alert.alert('⏰ Süre doldu', finished.map(f => f.label).join(', '));
    }, 500);
    return () => clearInterval(tick);
  }, [running]);

  if (!recipe) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: t.background, padding: 16 }}>
        {error ? <Text style={{ color: t.danger }}>{error}</Text> : <ActivityIndicator color={t.tint} />}
      </View>
    );
  }

  const total = recipe.steps.length;
  const text = step > 0 ? recipe.steps[step - 1] : '';
  const startTimer = (minutes: number) => {
    const timer = newTimer(step, minutes);
    setNow(timer.id);
    setTimers(cur => [...cur, timer]);
  };
  const go = (delta: number) => {
    Haptics.selectionAsync().catch(() => {});
    setStep(s => Math.min(total, Math.max(0, s + delta)));
  };
  const people = params.servings ? Number(params.servings) : recipe.servings;
  const big = (label: string, onPress: () => void, primary: boolean) => (
    <Pressable onPress={onPress} style={{ flex: 1, paddingVertical: 18, borderRadius: 18, alignItems: 'center',
      backgroundColor: primary ? t.tint : t.card, borderWidth: primary ? 0 : 1, borderColor: t.border }}>
      <Text style={{ color: primary ? '#fff' : t.text, fontSize: 18, fontWeight: '800' }}>{label}</Text>
    </Pressable>
  );

  return (
    <SafeAreaView edges={['bottom']} style={{ flex: 1, backgroundColor: t.background }}>
      <Stack.Screen options={{ title: recipe.name }} />
      {/* İlerleme çubuğu */}
      <View style={{ height: 6, backgroundColor: t.border }}>
        <View style={{ height: 6, width: `${(step / Math.max(total, 1)) * 100}%`, backgroundColor: t.tint }} />
      </View>

      {timers.length > 0 && (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, padding: 12, paddingBottom: 0 }}>
          {timers.map(x => (
            <Pressable key={x.id} onPress={() => setTimers(cur => cur.filter(y => y.id !== x.id))}
              accessibilityLabel={`${x.label} zamanlayıcısını kapat`}
              style={{ flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 8, borderRadius: 999,
                backgroundColor: x.done ? t.danger : t.card, borderWidth: 1, borderColor: x.done ? t.danger : t.tint }}>
              <Text style={{ color: x.done ? '#fff' : t.text, fontWeight: '800', fontVariant: ['tabular-nums'] }}>
                ⏱ {x.done ? 'Bitti!' : clock(x.endsAt - now)}
              </Text>
              <Text style={{ color: x.done ? '#fff' : t.textMuted, fontSize: 12 }}>{x.label} ✕</Text>
            </Pressable>
          ))}
        </View>
      )}

      <ScrollView contentContainerStyle={{ padding: 20, gap: 18, flexGrow: 1 }}>
        {step === 0 ? (
          <>
            <Text style={{ color: t.tint, fontWeight: '800' }}>HAZIRLIK · {total} ADIM</Text>
            <Text style={{ color: t.text, fontSize: 26, fontWeight: '800' }}>Malzemeleri hazırla</Text>
            {people !== recipe.servings && <Muted>Ölçüler {recipe.servings} kişilik; {people} kişi için oranlayın.</Muted>}
            <Muted>Hazırladığına dokun, işaretlensin.</Muted>
            {recipe.ingredients.map(i => {
              const done = ready.includes(i.name);
              return (
                <Pressable key={i.name} onPress={() => setReady(cur => done ? cur.filter(n => n !== i.name) : [...cur, i.name])}
                  style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 6 }}>
                  <View style={{ width: 28, height: 28, borderRadius: 8, borderWidth: 2, borderColor: done ? t.tint : t.border,
                    backgroundColor: done ? t.tint : 'transparent', alignItems: 'center', justifyContent: 'center' }}>
                    {done && <Text style={{ color: '#fff', fontWeight: '900' }}>✓</Text>}
                  </View>
                  <Text style={{ color: done ? t.textMuted : t.text, fontSize: 19, flex: 1, textDecorationLine: done ? 'line-through' : 'none' }}>
                    {i.name}
                  </Text>
                  <Text style={{ color: t.textMuted, fontSize: 16 }}>{i.amount_text}</Text>
                </Pressable>
              );
            })}
          </>
        ) : (
          <>
            <Text style={{ color: t.tint, fontWeight: '800' }}>ADIM {step} / {total}</Text>
            <Text style={{ color: t.text, fontSize: 28, lineHeight: 40, fontWeight: '600' }}>{text}</Text>
            {stepTimers(text).map(minutes => (
              <Pressable key={minutes} onPress={() => startTimer(minutes)}
                style={{ alignSelf: 'flex-start', paddingHorizontal: 18, paddingVertical: 12, borderRadius: 999, borderWidth: 2, borderColor: t.tint }}>
                <Text style={{ color: t.tint, fontSize: 18, fontWeight: '800' }}>⏱ {minutes} dk zamanlayıcı başlat</Text>
              </Pressable>
            ))}
            {step === total && <Text style={{ color: t.text, fontSize: 22, fontWeight: '800', marginTop: 12 }}>Afiyet olsun! 🎉</Text>}
          </>
        )}
      </ScrollView>

      <View style={{ flexDirection: 'row', gap: 12, padding: 16 }}>
        {step > 0 && big('‹ Geri', () => go(-1), false)}
        {step < total
          ? big(step === 0 ? 'Başla ›' : 'İleri ›', () => go(1), true)
          : big('Bitir ✓', () => router.back(), true)}
      </View>
    </SafeAreaView>
  );
}
