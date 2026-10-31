import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, ScrollView, Switch, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import ListPicker from '@/components/ListPicker';
import MealCostCard from '@/components/MealCostCard';
import NutritionCard from '@/components/NutritionCard';
import { Button, Card, Muted, useTheme } from '@/components/ui';
import { ALLERGEN_LABELS, api, COURSE_LABELS, formatSize, DIET_LABELS, MEAL_SLOT_LABELS, MealPlanDetail, MealSlot, SLOT_COURSES } from '@/lib/api';

const dayLabel = (d: Date) => d.toLocaleDateString('tr-TR', { weekday: 'long', day: 'numeric', month: 'long' });

/** Plan: günlere göre öğünler, "Başka öner", maliyet ve alışveriş listesine aktarma */
export default function MealPlanScreen() {
  const t = useTheme();
  const { id } = useLocalSearchParams<{ id: string }>();
  const planId = Number(id);
  const [plan, setPlan] = useState<MealPlanDetail | null>(null);
  const [includePantry, setIncludePantry] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [changing, setChanging] = useState<string | null>(null);
  const [picker, setPicker] = useState(false);
  const [exporting, setExporting] = useState(false);

  const load = useCallback(() => api.mealPlan(planId, includePantry)
    .then(p => { setPlan(p); setError(null); })
    .catch(e => setError((e as Error).message)), [planId, includePantry]);
  useEffect(() => { load(); }, [load]);

  // Gün -> öğün -> yemekler. Bütün yemekleri kaldırılan öğün de görünür ki geri eklenebilsin.
  const days = useMemo(() => {
    if (!plan) return [];
    const order: MealSlot[] = ['kahvalti', 'ogle', 'ara', 'aksam'];
    return Array.from({ length: plan.days }, (_, day) => {
      const entries = plan.entries.filter(e => e.day_index === day);
      const slots = order.filter(s => plan.meal_slots.includes(s) || entries.some(e => e.slot === s));
      const date = new Date(plan.start_date + 'T12:00:00');
      date.setDate(date.getDate() + day);
      // Yemek yapılmayan gün (ör. hafta sonu seçilmedi): içinde yemek yoksa gösterilmez
      const off = plan.weekdays.length > 0 && !plan.weekdays.includes((date.getDay() + 6) % 7) && !entries.length;
      return { day, date, off, meals: slots.map(slot => ({ slot, entries: entries.filter(e => e.slot === slot) })) };
    }).filter(d => !d.off);
  }, [plan]);

  const run = async (key: string, fn: () => Promise<MealPlanDetail>) => {
    setChanging(key);
    try {
      await fn();
      await load();
    } catch (e) { setError((e as Error).message); } finally { setChanging(null); }
  };


  const exportTo = async (listId: number | null) => {
    setExporting(true);
    try {
      const out = await api.exportMealPlan(planId, { list_id: listId, include_pantry: includePantry });
      setPicker(false);
      const open = () => router.push({ pathname: '/list/[id]', params: { id: String(out.list.id) } });
      const notes = [`${out.added} ürün eklendi.`];
      if (out.skipped.length) notes.push(`Marketlerinizde bulunamadığı için eklenmedi: ${out.skipped.join(', ')}.`);
      if (out.stored?.length) {
        notes.push(`Paketlerden artacaklar dolabına kaydedildi, sonraki planlar önce bunları kullanır: ${out.stored.map(s => `${s.name} ${formatSize(s.quantity, s.unit)}`).join(', ')}.`);
      }
      if (out.skipped.length || out.stored?.length) {
        Alert.alert('Listeye aktarıldı', notes.join('\n\n'), [{ text: 'Listeyi aç', onPress: open }]);
      } else open();
      load();
    } finally { setExporting(false); }
  };

  const remove = () => Alert.alert('Planı sil', 'Bu yemek planı silinsin mi?', [
    { text: 'Vazgeç', style: 'cancel' },
    { text: 'Sil', style: 'destructive', onPress: async () => { await api.deleteMealPlan(planId); router.back(); } },
  ]);

  if (!plan) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: t.background, padding: 16 }}>
        {error ? <Text style={{ color: t.danger }}>{error}</Text> : <ActivityIndicator color={t.tint} />}
      </View>
    );
  }

  return (
    <SafeAreaView edges={[]} style={{ flex: 1, backgroundColor: t.background }}>
      <Stack.Screen options={{ title: plan.name }} />
      <ScrollView>
        <View style={{ padding: 16, gap: 16 }}>
          <Muted>{plan.days} gün · {plan.servings} kişilik · {plan.meal_slots.map(s => MEAL_SLOT_LABELS[s]).join(', ')}. İstemediğiniz yemeği ✕ ile kaldırın, 🔄 ile değiştirin.</Muted>
          {(plan.diets.length > 0 || plan.avoid_allergens.length > 0) && (
            <Muted>
              {[...plan.diets.map(d => DIET_LABELS[d]), ...plan.avoid_allergens.map(a => `${ALLERGEN_LABELS[a]} yok`)].join(' · ')}
            </Muted>
          )}
          {(plan.leftovers || plan.low_waste || plan.have.length > 0) && (
            <Muted>
              {[plan.leftovers && '♻️ Bir pişir iki ye', plan.low_waste && '🧩 Az israf', plan.have.length > 0 && `🧺 Evde: ${plan.have.join(', ')}`]
                .filter(Boolean).join(' · ')}
            </Muted>
          )}
          {plan.budget_status && (
            <Card style={{ gap: 4, borderColor: plan.budget_status.within ? t.tint : t.danger, borderWidth: 1 }}>
              <Text style={{ color: plan.budget_status.within ? t.tint : t.danger, fontWeight: '800', fontSize: 16 }}>
                {plan.budget_status.within ? '✓ Bütçeye uyuyor' : '⚠️ Bütçe aşılıyor'}
              </Text>
              <Muted>
                Bütçe {Number(plan.budget_status.budget).toFixed(2)} ₺ · Alışveriş {Number(plan.budget_status.total).toFixed(2)} ₺
                {plan.budget_status.within ? '' : ` (${(Number(plan.budget_status.total) - Number(plan.budget_status.budget)).toFixed(2)} ₺ fazla)`}
              </Muted>
              {plan.budget_status.swaps > 0 && <Muted style={{ fontSize: 12 }}>Bütçe için {plan.budget_status.swaps} yemek daha ucuzuyla değiştirildi ya da çıkarıldı.</Muted>}
              {!plan.budget_status.within && <Muted style={{ fontSize: 12 }}>Kişi sayısını azaltmayı ya da tatlı ve içeceği çıkarmayı deneyin.</Muted>}
            </Card>
          )}
          {error && <Text style={{ color: t.danger }}>{error}</Text>}

          {days.map(({ day, date, meals }) => (
            <Card key={day} style={{ gap: 12 }}>
              <Text style={{ color: t.text, fontWeight: '800', fontSize: 16, textTransform: 'capitalize' }}>{dayLabel(date)}</Text>
              {meals.map(({ slot, entries }) => {
                const hasMain = entries.some(e => e.course === 'ana');
                // Yan yemek (pilav, püre) yalnız ana yemek varken eklenebilir
                const missing = SLOT_COURSES[slot].filter(c => !entries.some(e => e.course === c) && (c !== 'yan' || hasMain));
                return (
                  <View key={slot} style={{ gap: 8 }}>
                    <Text style={{ color: t.tint, fontWeight: '800', fontSize: 13 }}>{MEAL_SLOT_LABELS[slot].toLocaleUpperCase('tr-TR')}</Text>
                    {entries.map(e => (
                      <View key={e.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                        <Pressable style={{ flex: 1, flexDirection: 'row', alignItems: 'center', gap: 10 }}
                          onPress={() => router.push({ pathname: '/recipe/[id]', params: { id: String(e.recipe.id), servings: String(plan.servings) } })}>
                          <Text style={{ fontSize: 26 }}>{e.recipe.icon ?? '🍽️'}</Text>
                          <View style={{ flex: 1 }}>
                            <Muted style={{ fontSize: 12 }}>{COURSE_LABELS[e.course]}</Muted>
                            <Text style={{ color: t.text, fontWeight: '600' }}>{e.recipe.name}</Text>
                            {e.leftover_of != null && <Text style={{ color: t.tint, fontSize: 12, fontWeight: '600' }}>♻️ Dünden kalan, pişirmek yok</Text>}
                            {e.leftover_for.length > 0 && <Text style={{ color: t.tint, fontSize: 12, fontWeight: '600' }}>♻️ İki kat pişir, yarına kalsın</Text>}
                          </View>
                        </Pressable>
                        {changing === 'e' + e.id ? <ActivityIndicator color={t.tint} /> : (
                          <>
                            <Pressable onPress={() => run('e' + e.id, () => api.changeMealEntry(planId, e.id))} disabled={changing != null}
                              hitSlop={6} accessibilityLabel="Başka öner"
                              style={{ paddingHorizontal: 10, paddingVertical: 6, borderRadius: 999, borderWidth: 1, borderColor: t.border }}>
                              <Text style={{ color: t.tint, fontWeight: '600', fontSize: 13 }}>🔄 Değiştir</Text>
                            </Pressable>
                            <Pressable onPress={() => run('e' + e.id, () => api.removeMealEntry(planId, e.id))} disabled={changing != null}
                              hitSlop={6} accessibilityLabel={`${COURSE_LABELS[e.course]} istemiyorum`}
                              style={{ width: 32, height: 32, borderRadius: 16, borderWidth: 1, borderColor: t.border, alignItems: 'center', justifyContent: 'center' }}>
                              <Text style={{ color: t.danger, fontSize: 15, fontWeight: '700' }}>✕</Text>
                            </Pressable>
                          </>
                        )}
                      </View>
                    ))}
                    {missing.length > 0 && (
                      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
                        {missing.map(c => (
                          <Pressable key={c} disabled={changing != null}
                            onPress={() => run(`a${day}${slot}${c}`, () => api.addMealEntry(planId, day, slot, c))}
                            style={{ paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999, borderWidth: 1, borderStyle: 'dashed', borderColor: t.border }}>
                            {changing === `a${day}${slot}${c}` ? <ActivityIndicator color={t.tint} />
                              : <Text style={{ color: t.textMuted, fontSize: 12 }}>+ {COURSE_LABELS[c]}</Text>}
                          </Pressable>
                        ))}
                      </View>
                    )}
                  </View>
                );
              })}
            </Card>
          ))}

          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
            <Text style={{ color: t.text, flex: 1 }}>Evdekileri de hesapla (tuz, baharat)</Text>
            <Switch value={includePantry} onValueChange={setIncludePantry} trackColor={{ true: t.tint }} />
          </View>

          {plan.daily_nutrition && (
            <NutritionCard nutrition={plan.daily_nutrition} title="Kişi başı, günde (plandaki öğünler)"
              note="Plandaki yemeklerin yaklaşık değerleri toplanıp gün sayısına bölündü." />
          )}

          <MealCostCard cost={plan.cost} />

          <Button title="🛒 Alışveriş listesine aktar" onPress={() => setPicker(true)} busy={exporting} />
          <Button title="Yeni liste olarak aktar" kind="secondary" onPress={() => exportTo(null).catch(e => setError(e.message))} busy={exporting} />
          {plan.exported_list_id != null && (
            <Text style={{ color: t.tint, textAlign: 'center', fontWeight: '600' }}
              onPress={() => router.push({ pathname: '/list/[id]', params: { id: String(plan.exported_list_id) } })}>
              Son aktarılan listeyi aç ›
            </Text>
          )}
          <Text style={{ color: t.danger, textAlign: 'center', marginTop: 8 }} onPress={remove}>Planı sil</Text>
        </View>
      </ScrollView>
      <ListPicker visible={picker} onClose={() => setPicker(false)} onPick={id => exportTo(id)} />
    </SafeAreaView>
  );
}
