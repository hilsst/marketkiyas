import { setAudioModeAsync, useAudioPlayer } from 'expo-audio';
import { useKeepAwake } from 'expo-keep-awake';
import * as Haptics from 'expo-haptics';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, Vibration, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import Icon from '@/components/Icon';
import { Muted, useTheme } from '@/components/ui';
import { api, RecipeDetail } from '@/lib/api';

/**
 * Adımda gerçekten beklenen süreler (saniye): "15 dakika", "20-25 dakika" (üst sınır), "1 saat", "30 saniye".
 * Aletin ısınması (fırını/ocağı ısıtmak) için sayaç yok, kullanıcı alet hazır olunca adımı kendisi geçer;
 * ama "15 dakika fırınlayın" gibi içeride tutma süreleri sayılır. "Bitmesine 3 dakika kala", "son 5 dakikada"
 * gibi tarifin içinden bir an belirten ifadeler de bekleme süresi değildir.
 */
export function stepTimers(text: string): number[] {
  const found: number[] = [];
  const re = /(\d+)(?:\s*[-–]\s*(\d+))?\s*(dakika|dk|saat|saniye|sn)/gi;
  for (const sentence of text.split(/[.!?]\s+/)) {
    const preheat = /ısıt/i.test(sentence) && !/(pişir|fırınla|fırında|bekle|kavur|kaynat|haşla)/i.test(sentence);
    if (preheat || /\bkala\b|\bson\s+\d+\s*(dakika|dk)/i.test(sentence)) continue;
    re.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(sentence)) !== null) {
      const value = Number(m[2] ?? m[1]);
      const unit = m[3].toLowerCase();
      const seconds = unit === 'saat' ? value * 3600 : unit === 'saniye' || unit === 'sn' ? value : value * 60;
      if (seconds > 0 && seconds <= 36000 && !found.includes(seconds)) found.push(seconds);
    }
  }
  return found;
}

/** Bir adımın sayacı: key = "adım:sıra"; endsAt boşsa henüz başlamadı */
interface Run { endsAt: number; done: boolean; }

const label = (seconds: number) => seconds >= 3600 && seconds % 3600 === 0 ? `${seconds / 3600} sa`
  : seconds % 60 === 0 ? `${seconds / 60} dk` : seconds < 60 ? `${seconds} sn` : `${Math.floor(seconds / 60)} dk ${seconds % 60} sn`;

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
  const [runs, setRuns] = useState<Record<string, Run>>({});
  const [now, setNow] = useState(() => Date.now());
  const runsRef = useRef<Record<string, Run>>({});
  const beeped = useRef<Record<string, number>>({});
  const tick = useAudioPlayer(require('@/assets/sounds/tick.wav'));
  const alarm = useAudioPlayer(require('@/assets/sounds/alarm.wav'));
  useEffect(() => { runsRef.current = runs; }, [runs]);
  useEffect(() => { setAudioModeAsync({ playsInSilentMode: true }).catch(() => {}); }, []);

  useEffect(() => {
    api.recipe(Number(params.id), params.servings ? Number(params.servings) : undefined)
      .then(setRecipe).catch(e => setError((e as Error).message));
  }, [params.id, params.servings]);

  const play = (player: typeof tick) => {
    try { player.seekTo(0); player.play(); } catch { /* ses çalınamazsa titreşim yine var */ }
  };

  const running = Object.values(runs).some(x => !x.done);
  useEffect(() => {
    if (!running) return;
    const loop = setInterval(() => {
      const at = Date.now();
      setNow(at);
      const finished: string[] = [];
      for (const [key, run] of Object.entries(runsRef.current)) {
        if (run.done) continue;
        const left = Math.ceil((run.endsAt - at) / 1000);
        if (left <= 0) finished.push(key);
        else if (left <= 5 && beeped.current[key] !== left) {
          // Son 5 saniye: her saniye kısa bip
          beeped.current[key] = left;
          play(tick);
          Haptics.selectionAsync().catch(() => {});
        }
      }
      if (!finished.length) return;
      setRuns(cur => {
        const next = { ...cur };
        for (const key of finished) if (next[key]) next[key] = { ...next[key], done: true };
        return next;
      });
      play(alarm);
      Vibration.vibrate([0, 600, 300, 600, 300, 600]);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    }, 250);
    return () => clearInterval(loop);
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
  const timers = stepTimers(text);
  const start = (key: string, seconds: number) => {
    const at = Date.now();
    delete beeped.current[key];
    setNow(at);
    setRuns(cur => ({ ...cur, [key]: { endsAt: at + seconds * 1000, done: false } }));
  };
  const clear = (key: string) => setRuns(cur => { const next = { ...cur }; delete next[key]; return next; });
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

      {/* Başka adımda çalışan sayaçlar: dokununca o adıma gider */}
      {Object.entries(runs).filter(([key]) => Number(key.split(':')[0]) !== step).length > 0 && (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, padding: 12, paddingBottom: 0 }}>
          {Object.entries(runs).filter(([key]) => Number(key.split(':')[0]) !== step).map(([key, run]) => (
            <Pressable key={key} onPress={() => setStep(Number(key.split(':')[0]))}
              style={{ flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 8, borderRadius: 999,
                backgroundColor: run.done ? t.danger : t.card, borderWidth: 1, borderColor: run.done ? t.danger : t.tint }}>
              <Text style={{ color: run.done ? '#fff' : t.text, fontWeight: '800', fontVariant: ['tabular-nums'] }}>
                {run.done ? 'Bitti!' : clock(run.endsAt - now)}
              </Text>
              <Text style={{ color: run.done ? '#fff' : t.textMuted, fontSize: 12 }}>Adım {key.split(':')[0]}</Text>
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
                    {done && <Icon name="check" size={16} color="#fff" />}
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
            {timers.length > 0 && (
              <View style={{ flex: 1, justifyContent: 'center', gap: 16, paddingVertical: 12 }}>
                {timers.map((seconds, i) => {
                  const key = `${step}:${i}`;
                  const run = runs[key];
                  const left = run ? Math.max(0, run.endsAt - now) : seconds * 1000;
                  const urgent = !!run && !run.done && Math.ceil(left / 1000) <= 5;
                  const accent = run?.done || urgent ? t.danger : t.tint;
                  return (
                    <View key={key} style={{ alignItems: 'center', gap: 14, paddingVertical: 28, paddingHorizontal: 16, borderRadius: 28,
                      backgroundColor: t.card, borderWidth: 2, borderColor: accent }}>
                      <Text style={{ color: t.textMuted, fontWeight: '700', letterSpacing: 0.6 }}>
                        {run?.done ? 'SÜRE DOLDU' : run ? 'KALAN SÜRE' : `SÜRE · ${label(seconds)}`}
                      </Text>
                      <Text style={{ color: accent, fontSize: urgent ? 84 : 72, fontWeight: '900', fontVariant: ['tabular-nums'] }}
                        accessibilityLabel={run?.done ? 'Süre doldu' : `${clock(left)} kaldı`}>
                        {run?.done ? '00:00' : clock(left)}
                      </Text>
                      <View style={{ alignSelf: 'stretch', height: 8, borderRadius: 4, backgroundColor: t.border, overflow: 'hidden' }}>
                        <View style={{ height: 8, width: `${run ? Math.min(100, ((seconds * 1000 - left) / (seconds * 1000)) * 100) : 0}%`, backgroundColor: accent }} />
                      </View>
                      <Pressable onPress={() => run ? clear(key) : start(key, seconds)}
                        style={{ paddingHorizontal: 28, paddingVertical: 14, borderRadius: 999, backgroundColor: run ? 'transparent' : t.tint,
                          borderWidth: run ? 2 : 0, borderColor: accent }}>
                        <Text style={{ color: run ? accent : '#fff', fontSize: 18, fontWeight: '800' }}>
                          {run?.done ? 'Kapat' : run ? 'Sıfırla' : 'Sayacı başlat'}
                        </Text>
                      </Pressable>
                    </View>
                  );
                })}
              </View>
            )}
            {step === total && <Text style={{ color: t.text, fontSize: 22, fontWeight: '800', marginTop: 12 }}>Afiyet olsun!</Text>}
          </>
        )}
      </ScrollView>

      <View style={{ flexDirection: 'row', gap: 12, padding: 16 }}>
        {step > 0 && big('‹ Geri', () => go(-1), false)}
        {step < total
          ? big(step === 0 ? 'Başla ›' : 'İleri ›', () => go(1), true)
          : big('Bitir', () => router.back(), true)}
      </View>
    </SafeAreaView>
  );
}
