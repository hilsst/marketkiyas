import { router, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button, Card, LoginPrompt, Muted, useTheme } from '@/components/ui';
import { api, Cuisine, MEAL_SLOT_LABELS, MealPlanSummary, MealSlot, PlanPeriod, RecipeSummary } from '@/lib/api';
import { useAuth } from '@/lib/auth';

const SLOTS: MealSlot[] = ['kahvalti', 'ogle', 'aksam'];

/** Yemek planlayıcı: günlük / haftalık plan oluştur, planlarım ve tarifler */
export default function MealsScreen() {
  const t = useTheme();
  const { user } = useAuth();
  const [cuisines, setCuisines] = useState<Cuisine[]>([]);
  const [recipes, setRecipes] = useState<RecipeSummary[]>([]);
  const [plans, setPlans] = useState<MealPlanSummary[]>([]);
  const [period, setPeriod] = useState<PlanPeriod>('weekly');
  const [cuisine, setCuisine] = useState<string | null>(null);
  const [servings, setServings] = useState(2);
  const [slots, setSlots] = useState<MealSlot[]>(['aksam']);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.cuisines().then(cs => {
      setCuisines(cs);
      setCuisine(c => c ?? cs.find(x => x.is_default)?.slug ?? cs[0]?.slug ?? null);
    }).catch(e => setError(e.message));
  }, []);
  useEffect(() => { api.recipes(cuisine).then(setRecipes).catch(() => setRecipes([])); }, [cuisine]);
  useFocusEffect(useCallback(() => {
    if (user) api.mealPlans().then(setPlans).catch(() => {});
  }, [user]));

  const toggleSlot = (slot: MealSlot) =>
    setSlots(cur => cur.includes(slot) ? (cur.length > 1 ? cur.filter(s => s !== slot) : cur) : [...cur, slot]);

  const create = async () => {
    setBusy(true);
    setError(null);
    try {
      const plan = await api.createMealPlan({ period, cuisine, servings, meal_slots: slots });
      router.push({ pathname: '/meals/[id]', params: { id: String(plan.id) } });
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  const chip = (key: string, active: boolean, label: string, onPress: () => void) => (
    <Pressable key={key} onPress={onPress} style={{ paddingHorizontal: 14, paddingVertical: 9, borderRadius: 999, borderWidth: 1,
      borderColor: active ? t.tint : t.border, backgroundColor: active ? t.tint : t.card }}>
      <Text style={{ color: active ? '#fff' : t.text, fontWeight: '600' }}>{label}</Text>
    </Pressable>
  );
  const sectionTitle = (text: string) => <Text style={{ color: t.text, fontWeight: '800', fontSize: 17 }}>{text}</Text>;

  return (
    <SafeAreaView edges={[]} style={{ flex: 1, backgroundColor: t.background }}>
      <ScrollView>
        <View style={{ padding: 16, gap: 16 }}>
          <Muted>Günlük ya da haftalık yemek planı yap; malzemelerin marketlerindeki en uygun fiyatla maliyetini gör, istersen alışveriş listene aktar.</Muted>

          {user ? (
            <Card style={{ gap: 14 }}>
              {sectionTitle('🍲 Yeni plan')}
              <View style={{ flexDirection: 'row', gap: 8 }}>
                {chip('weekly', period === 'weekly', 'Haftalık (7 gün)', () => setPeriod('weekly'))}
                {chip('daily', period === 'daily', 'Günlük', () => setPeriod('daily'))}
              </View>

              {cuisines.length > 0 && (
                <View style={{ gap: 6 }}>
                  <Muted>Mutfak</Muted>
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                    {cuisines.map(c => chip(c.slug, cuisine === c.slug, `${c.icon ?? ''} ${c.name}`.trim(), () => setCuisine(c.slug)))}
                  </View>
                </View>
              )}

              <View style={{ gap: 6 }}>
                <Muted>Öğünler</Muted>
                <View style={{ flexDirection: 'row', gap: 8 }}>
                  {SLOTS.map(s => chip(s, slots.includes(s), MEAL_SLOT_LABELS[s], () => toggleSlot(s)))}
                </View>
              </View>

              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                <Muted style={{ flex: 1 }}>Kaç kişilik?</Muted>
                <Pressable onPress={() => setServings(n => Math.max(1, n - 1))} hitSlop={8}
                  style={{ width: 36, height: 36, borderRadius: 18, borderWidth: 1, borderColor: t.border, alignItems: 'center', justifyContent: 'center' }}>
                  <Text style={{ color: t.text, fontSize: 20 }}>−</Text>
                </Pressable>
                <Text style={{ color: t.text, fontSize: 18, fontWeight: '800', minWidth: 28, textAlign: 'center' }}>{servings}</Text>
                <Pressable onPress={() => setServings(n => Math.min(12, n + 1))} hitSlop={8}
                  style={{ width: 36, height: 36, borderRadius: 18, borderWidth: 1, borderColor: t.border, alignItems: 'center', justifyContent: 'center' }}>
                  <Text style={{ color: t.text, fontSize: 20 }}>+</Text>
                </Pressable>
              </View>

              {error && <Text style={{ color: t.danger }}>{error}</Text>}
              <Button title="Plan oluştur" onPress={create} busy={busy} />
            </Card>
          ) : (
            <LoginPrompt what="Yemek planı yapmak" />
          )}

          {plans.length > 0 && (
            <View style={{ gap: 10 }}>
              {sectionTitle('Planlarım')}
              {plans.map(p => (
                <Pressable key={p.id} onPress={() => router.push({ pathname: '/meals/[id]', params: { id: String(p.id) } })}>
                  <Card style={{ gap: 2 }}>
                    <Text style={{ color: t.text, fontWeight: '700' }}>{p.name}</Text>
                    <Muted>{p.days} gün · {p.entry_count} öğün · {p.servings} kişilik{p.exported_list_id ? ' · listeye aktarıldı' : ''}</Muted>
                  </Card>
                </Pressable>
              ))}
            </View>
          )}

          {recipes.length > 0 && (
            <View style={{ gap: 10 }}>
              {sectionTitle('Tarifler')}
              {recipes.map(r => (
                <Pressable key={r.id} onPress={() => router.push({ pathname: '/recipe/[id]', params: { id: String(r.id) } })}>
                  <Card style={{ flexDirection: 'row', gap: 12, alignItems: 'center' }}>
                    <Text style={{ fontSize: 34 }}>{r.icon ?? '🍽️'}</Text>
                    <View style={{ flex: 1, gap: 2 }}>
                      <Text style={{ color: t.text, fontWeight: '700' }}>{r.name}</Text>
                      <Muted>{r.course} · {r.prep_minutes + r.cook_minutes} dk · {r.meal_slots.map(s => MEAL_SLOT_LABELS[s]).join(', ')}</Muted>
                    </View>
                  </Card>
                </Pressable>
              ))}
            </View>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
