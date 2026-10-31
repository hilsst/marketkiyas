import { router, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import CuisinePicker from '@/components/CuisinePicker';
import { Button, Card, LoginPrompt, Muted, useTheme } from '@/components/ui';
import {
  Allergen, ALLERGEN_LABELS, api, COURSE_LABELS, CourseType, Cuisine, Diet, DIET_LABELS, MEAL_SLOT_LABELS, MealPlanSummary, MealSlot,
  PlanPeriod, RecipeSummary,
} from '@/lib/api';
import { useAuth } from '@/lib/auth';

const SLOTS: MealSlot[] = ['kahvalti', 'ogle', 'ara', 'aksam'];
const COURSES: CourseType[] = ['corba', 'ana', 'yan', 'salata', 'tatli', 'icecek'];
const COURSE_ICONS: Record<CourseType, string> = { corba: '🥣', ana: '🍛', yan: '🍚', salata: '🥗', tatli: '🍮', icecek: '🥤', ara: '🍎' };
// Glutensiz ayrı bir seçenek değil: alerji listesindeki "Gluten" aynı işi görür
const DIETS: Diet[] = ['vejetaryen', 'vegan'];
const ALLERGENS: Allergen[] = ['gluten', 'sut', 'yumurta', 'kuruyemis', 'susam', 'balik'];

/** Yemek planlayıcı: günlük / haftalık plan oluştur, planlarım ve tarifler */
export default function MealsScreen() {
  const t = useTheme();
  const { user } = useAuth();
  const [cuisines, setCuisines] = useState<Cuisine[]>([]);
  const [recipes, setRecipes] = useState<RecipeSummary[]>([]);
  const [plans, setPlans] = useState<MealPlanSummary[]>([]);
  const [period, setPeriod] = useState<PlanPeriod>('weekly');
  // Son seçilen mutfaklar; mutfak seçim kartı bunlarla açılır
  const [chosen, setChosen] = useState<string[]>([]);
  const [picking, setPicking] = useState(false);
  // Tarifler bölümünde gösterilen mutfak (null = hepsi)
  const [browse, setBrowse] = useState<string | null>(null);
  const [servings, setServings] = useState(2);
  const [slots, setSlots] = useState<MealSlot[]>(['aksam']);
  const [courses, setCourses] = useState<CourseType[]>(COURSES);
  const [diets, setDiets] = useState<Diet[]>([]);
  const [avoid, setAvoid] = useState<Allergen[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.cuisines().then(cs => {
      setCuisines(cs);
      setChosen(c => c.length ? c : cs.filter(x => x.is_default && x.recipe_count > 0).map(x => x.slug));
    }).catch(e => setError(e.message));
  }, []);
  // Tarifler de seçilen diyete göre süzülür ki kullanıcı ne çıkacağını görsün
  useEffect(() => { api.recipes(browse, diets, avoid).then(setRecipes).catch(() => setRecipes([])); }, [browse, diets, avoid]);
  const cuisineOf = (slug: string) => cuisines.find(c => c.slug === slug);
  useFocusEffect(useCallback(() => {
    if (user) api.mealPlans().then(setPlans).catch(() => {});
  }, [user]));

  const toggleSlot = (slot: MealSlot) =>
    setSlots(cur => cur.includes(slot) ? (cur.length > 1 ? cur.filter(s => s !== slot) : cur) : [...cur, slot]);

  const toggleCourse = (course: CourseType) =>
    setCourses(cur => cur.includes(course) ? (cur.length > 1 ? cur.filter(c => c !== course) : cur) : [...cur, course]);

  const toggle = <T,>(set: (fn: (cur: T[]) => T[]) => void, value: T) =>
    set(cur => cur.includes(value) ? cur.filter(v => v !== value) : [...cur, value]);

  const create = async (selected: string[]) => {
    setBusy(true);
    setError(null);
    setChosen(selected);
    try {
      const plan = await api.createMealPlan({ period, cuisines: selected, servings, meal_slots: slots, courses, diets, avoid_allergens: avoid });
      setPicking(false);
      router.push({ pathname: '/meals/[id]', params: { id: String(plan.id) } });
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const openPicker = () => { setError(null); setPicking(true); };

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

              <View style={{ gap: 6 }}>
                <Muted>Öğünler</Muted>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                  {SLOTS.map(s => chip(s, slots.includes(s), MEAL_SLOT_LABELS[s], () => toggleSlot(s)))}
                </View>
              </View>

              <View style={{ gap: 6 }}>
                <Muted>Menüde neler olsun? İstemediğinize dokunup çıkarın.</Muted>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                  {COURSES.map(c => chip(c, courses.includes(c), `${COURSE_ICONS[c]} ${COURSE_LABELS[c]}`, () => toggleCourse(c)))}
                </View>
                {courses.includes('yan') && <Muted style={{ fontSize: 12 }}>Yanında: pilav, makarna, püre gibi, yalnız uyduğu ana yemekle önerilir (ör. kuru fasulyeye pilav; mantıya önerilmez).</Muted>}
                {courses.includes('icecek') && <Muted style={{ fontSize: 12 }}>İçecek, ana yemekle uyumlu hazır içeceklerden seçilir (ör. kuru fasulyeye ayran).</Muted>}
              </View>

              <View style={{ gap: 6 }}>
                <Muted>Beslenme şekli (isteğe bağlı)</Muted>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                  {DIETS.map(d => chip(d, diets.includes(d), DIET_LABELS[d], () => toggle(setDiets, d)))}
                </View>
              </View>

              <View style={{ gap: 6 }}>
                <Muted>Alerjim var, bunlar olmasın</Muted>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                  {ALLERGENS.map(a => chip(a, avoid.includes(a), `🚫 ${ALLERGEN_LABELS[a]}`, () => toggle(setAvoid, a)))}
                </View>
                {(diets.length > 0 || avoid.length > 0) && (
                  <Muted style={{ fontSize: 12 }}>Paketli ürünlerin etiketini yine de kontrol edin; alerjen bilgisi tarifteki malzemelere göredir.</Muted>
                )}
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

              {error && !picking && <Text style={{ color: t.danger }}>{error}</Text>}
              <Button title="Plan oluştur" onPress={openPicker} busy={busy} />
              <Muted style={{ fontSize: 12, textAlign: 'center', marginTop: -6 }}>Sonraki adımda mutfakları seçeceksiniz (Türk, İtalyan, Uzak Doğu...)</Muted>
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
                    {(p.cuisines?.length ?? 0) > 0 && (
                      <Muted style={{ fontSize: 12 }}>{p.cuisines.map(s => cuisineOf(s)?.icon ?? '').join(' ')} {p.cuisines.map(s => cuisineOf(s)?.name ?? s).join(', ')}</Muted>
                    )}
                  </Card>
                </Pressable>
              ))}
            </View>
          )}

          {(recipes.length > 0 || browse) && (
            <View style={{ gap: 10 }}>
              {sectionTitle('Tarifler')}
              <Muted style={{ marginTop: -4 }}>En sevilenler önde. Beğendiğiniz tarifi ❤️ ile işaretleyin; planlarda daha sık önerilir.</Muted>
              {cuisines.length > 1 && (
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginHorizontal: -16 }}
                  contentContainerStyle={{ paddingHorizontal: 16, gap: 8 }}>
                  {chip('all', browse === null, '🌍 Hepsi', () => setBrowse(null))}
                  {cuisines.filter(c => c.recipe_count > 0).map(c =>
                    chip(c.slug, browse === c.slug, `${c.icon ?? ''} ${c.name}`.trim(), () => setBrowse(c.slug)))}
                </ScrollView>
              )}
              {recipes.length === 0 && <Muted>Bu mutfakta seçimlerinize uyan tarif yok.</Muted>}
              {(['corba', 'ana', 'yan', 'salata', 'tatli', 'icecek', 'ara'] as CourseType[]).map(course => {
                const group = recipes.filter(r => r.course_type === course);
                if (!group.length) return null;
                return (
                  <View key={course} style={{ gap: 6 }}>
                    <Muted style={{ fontWeight: '700' }}>{COURSE_ICONS[course]} {COURSE_LABELS[course]}</Muted>
                    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginHorizontal: -16 }}
                      contentContainerStyle={{ paddingHorizontal: 16, gap: 8 }}>
                      {group.map(r => (
                        <Pressable key={r.id} onPress={() => router.push({ pathname: '/recipe/[id]', params: { id: String(r.id) } })}>
                          <Card style={{ width: 132, gap: 4, padding: 12 }}>
                            <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                              <Text style={{ fontSize: 30 }}>{r.icon ?? '🍽️'}</Text>
                              {browse === null && <Text style={{ fontSize: 14 }}>{cuisineOf(r.cuisine)?.icon ?? ''}</Text>}
                            </View>
                            <Text style={{ color: t.text, fontWeight: '700' }} numberOfLines={2}>{r.name}</Text>
                            <Muted style={{ fontSize: 12 }}>
                              {r.prep_minutes + r.cook_minutes > 0 ? `${r.prep_minutes + r.cook_minutes} dk` : 'Hazır'}
                              {r.nutrition ? ` · ${r.nutrition.kcal} kcal` : ''}
                            </Muted>
                            {(r.liked || r.like_count > 0) && <Muted style={{ fontSize: 12 }}>{r.liked ? '❤️' : '🤍'} {r.like_count}</Muted>}
                          </Card>
                        </Pressable>
                      ))}
                    </ScrollView>
                  </View>
                );
              })}
            </View>
          )}
        </View>
      </ScrollView>
      {picking && (
        <CuisinePicker cuisines={cuisines} initial={chosen} period={period} busy={busy} error={error}
          onCancel={() => setPicking(false)} onConfirm={create} />
      )}
    </SafeAreaView>
  );
}
