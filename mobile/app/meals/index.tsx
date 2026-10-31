import { router, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, Switch, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import CuisinePicker from '@/components/CuisinePicker';
import PantryPicker from '@/components/PantryPicker';
import { Button, Card, Input, LoginPrompt, Muted, useTheme } from '@/components/ui';
import {
  Allergen, ALLERGEN_LABELS, api, COURSE_LABELS, CourseType, Cuisine, Diet, DIET_LABELS, MEAL_SLOT_LABELS, MealPlanSummary, MealSlot,
  RecipeSummary, WEEKDAY_SHORT,
} from '@/lib/api';
import { useAuth } from '@/lib/auth';

const SLOTS: MealSlot[] = ['kahvalti', 'ogle', 'ara', 'aksam'];
const COURSES: CourseType[] = ['corba', 'ana', 'yan', 'salata', 'tatli', 'icecek'];
const COURSE_ICONS: Record<CourseType, string> = { corba: '🥣', ana: '🍛', yan: '🍚', salata: '🥗', tatli: '🍮', icecek: '🥤', ara: '🍎' };
// Glutensiz ayrı bir seçenek değil: alerji listesindeki "Gluten" aynı işi görür
const DIETS: Diet[] = ['vejetaryen', 'vegan'];
const ALLERGENS: Allergen[] = ['gluten', 'sut', 'yumurta', 'kuruyemis', 'susam', 'balik'];
// Plan süresi (gün); 14'e kadar, ör. maaş gününe kadar 10 gün
const LENGTHS = [1, 2, 3, 5, 7, 10, 14];
const ALL_DAYS = [0, 1, 2, 3, 4, 5, 6];

/** Yemek planlayıcı: 1-14 günlük plan oluştur (bütçe, kalan yemek, dolaptakiler), planlarım ve tarifler */
export default function MealsScreen() {
  const t = useTheme();
  const { user } = useAuth();
  const [cuisines, setCuisines] = useState<Cuisine[]>([]);
  const [recipes, setRecipes] = useState<RecipeSummary[]>([]);
  const [plans, setPlans] = useState<MealPlanSummary[]>([]);
  const [stockCount, setStockCount] = useState(0);
  const [days, setDays] = useState(7);
  const [weekdays, setWeekdays] = useState<number[]>(ALL_DAYS);
  const [budget, setBudget] = useState('');
  const [leftovers, setLeftovers] = useState(false);
  const [lowWaste, setLowWaste] = useState(false);
  const [have, setHave] = useState<string[]>([]);
  const [pantryOpen, setPantryOpen] = useState(false);
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
    if (user) {
      api.mealPlans().then(setPlans).catch(() => {});
      api.pantry().then(p => setStockCount(p.length)).catch(() => {});
    }
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
      const amount = Number(budget.replace(',', '.'));
      const plan = await api.createMealPlan({
        period: days === 1 ? 'daily' : days === 7 ? 'weekly' : 'custom', days, cuisines: selected, servings, meal_slots: slots, courses,
        diets, avoid_allergens: avoid, weekdays: days > 1 && weekdays.length < 7 ? weekdays : [],
        budget: amount > 0 ? amount : null, leftovers, low_waste: lowWaste, have,
      });
      setPicking(false);
      router.push({ pathname: '/meals/[id]', params: { id: String(plan.id) } });
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const openPicker = () => {
    if (days > 1 && !weekdays.length) { setError('En az bir gün seçin.'); return; }
    setError(null); setPicking(true);
  };
  const toggleDay = (d: number) => setWeekdays(cur => cur.includes(d) ? cur.filter(x => x !== d) : [...cur, d].sort());
  const option = (key: string, value: boolean, onChange: (v: boolean) => void, title: string, note: string) => (
    <View key={key} style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
      <View style={{ flex: 1 }}>
        <Text style={{ color: t.text, fontWeight: '700' }}>{title}</Text>
        <Muted style={{ fontSize: 12 }}>{note}</Muted>
      </View>
      <Switch value={value} onValueChange={onChange} trackColor={{ true: t.tint }} />
    </View>
  );

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
          <Muted>1 ile 14 gün arası yemek planı yap; bütçeni, evdeki malzemeleri ve artan yemeği hesaba kat. Maliyet marketlerindeki en uygun fiyatla hesaplanır, istersen alışveriş listene aktar.</Muted>

          {user ? (
            <Card style={{ gap: 14 }}>
              {sectionTitle('🍲 Yeni plan')}
              <View style={{ gap: 6 }}>
                <Muted>Kaç günlük?</Muted>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                  {LENGTHS.map(n => chip('d' + n, days === n, n === 1 ? 'Bugün' : n === 7 ? '1 hafta' : n === 14 ? '2 hafta' : `${n} gün`, () => setDays(n)))}
                </View>
              </View>

              {days > 1 && (
                <View style={{ gap: 6 }}>
                  <Muted>Hangi günler yemek yapılacak?</Muted>
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
                    {ALL_DAYS.map(d => chip('w' + d, weekdays.includes(d), WEEKDAY_SHORT[d], () => toggleDay(d)))}
                  </View>
                  <View style={{ flexDirection: 'row', gap: 14 }}>
                    <Text style={{ color: t.tint, fontWeight: '600', fontSize: 13 }} onPress={() => setWeekdays([0, 1, 2, 3, 4])}>Hafta içi</Text>
                    <Text style={{ color: t.tint, fontWeight: '600', fontSize: 13 }} onPress={() => setWeekdays([5, 6])}>Hafta sonu</Text>
                    <Text style={{ color: t.tint, fontWeight: '600', fontSize: 13 }} onPress={() => setWeekdays(ALL_DAYS)}>Her gün</Text>
                  </View>
                </View>
              )}

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

              <View style={{ gap: 6 }}>
                <Muted>Bütçe (isteğe bağlı)</Muted>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <Input style={{ flex: 1 }} placeholder="ör. 1500" keyboardType="numeric" value={budget}
                    onChangeText={v => setBudget(v.replace(/[^0-9.,]/g, ''))} />
                  <Text style={{ color: t.text, fontWeight: '800', fontSize: 18 }}>₺</Text>
                </View>
                <Muted style={{ fontSize: 12 }}>Alışveriş tutarı bütçeyi aşarsa pahalı yemekler ucuzlarıyla değiştirilir; yetmezse içecek ve tatlı çıkarılır.</Muted>
              </View>

              {option('leftovers', leftovers, setLeftovers, '♻️ Bir pişir, iki ye',
                slots.includes('ogle') ? 'Akşam yemeği iki kat pişer, ertesi gün öğlene kalır.' : 'Akşam yemeği iki kat pişer, ertesi akşama kalır.')}
              {option('lowWaste', lowWaste, setLowWaste, '🧩 Az israf',
                'Malzemesi ortak yemekler seçilir; aldığın maydanoz, yoğurt, peynir yarım kalmasın.')}

              <Pressable onPress={() => setPantryOpen(true)}
                style={{ flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, borderRadius: 14, borderWidth: 1, borderColor: have.length ? t.tint : t.border }}>
                <Text style={{ fontSize: 24 }}>🧺</Text>
                <View style={{ flex: 1 }}>
                  <Text style={{ color: t.text, fontWeight: '700' }}>Dolabımda ne var?</Text>
                  <Muted style={{ fontSize: 12 }} >
                    {have.length ? have.join(', ') : 'Evdeki malzemeleri seç; onları kullanan yemekler öne çıkar, listeye eklenmez.'}
                  </Muted>
                </View>
                <Text style={{ color: t.tint, fontWeight: '700' }}>{have.length ? 'Düzenle' : 'Seç'} ›</Text>
              </Pressable>

              {error && !picking && <Text style={{ color: t.danger }}>{error}</Text>}
              <Button title="Plan oluştur" onPress={openPicker} busy={busy} />
              <Muted style={{ fontSize: 12, textAlign: 'center', marginTop: -6 }}>Sonraki adımda mutfakları seçeceksiniz (Türk, İtalyan, Uzak Doğu...)</Muted>
            </Card>
          ) : (
            <LoginPrompt what="Yemek planı yapmak" />
          )}

          {user && stockCount > 0 && (
            <Pressable onPress={() => router.push('/meals/pantry')}>
              <Card style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                <Text style={{ fontSize: 28 }}>🧊</Text>
                <View style={{ flex: 1 }}>
                  <Text style={{ color: t.text, fontWeight: '700' }}>Dolabım: {stockCount} malzeme artmış</Text>
                  <Muted style={{ fontSize: 12 }}>Önceki alışverişten artanlar; yeni plan önce bunları kullanır.</Muted>
                </View>
                <Text style={{ color: t.tint, fontWeight: '700' }}>Gör ›</Text>
              </Card>
            </Pressable>
          )}

          {plans.length > 0 && (
            <View style={{ gap: 10 }}>
              {sectionTitle('Planlarım')}
              {plans.map(p => (
                <Pressable key={p.id} onPress={() => router.push({ pathname: '/meals/[id]', params: { id: String(p.id) } })}>
                  <Card style={{ gap: 2 }}>
                    <Text style={{ color: t.text, fontWeight: '700' }}>{p.name}</Text>
                    <Muted>{p.days} gün · {p.entry_count} öğün · {p.servings} kişilik{p.budget ? ` · ${Number(p.budget).toFixed(0)} ₺ bütçe` : ''}{p.exported_list_id ? ' · listeye aktarıldı' : ''}</Muted>
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
        <CuisinePicker cuisines={cuisines} initial={chosen} days={days} busy={busy} error={error}
          onCancel={() => setPicking(false)} onConfirm={create} />
      )}
      {pantryOpen && <PantryPicker initial={have} onClose={h => { setHave(h); setPantryOpen(false); }} />}
    </SafeAreaView>
  );
}
