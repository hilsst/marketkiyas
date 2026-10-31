import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, ScrollView, Switch, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import ListPicker from '@/components/ListPicker';
import MealCostCard from '@/components/MealCostCard';
import { Button, Card, Muted, useTheme } from '@/components/ui';
import { api, MEAL_SLOT_LABELS, MealPlanDetail, MealPlanEntry } from '@/lib/api';

const dayLabel = (iso: string) =>
  new Date(iso + 'T12:00:00').toLocaleDateString('tr-TR', { weekday: 'long', day: 'numeric', month: 'long' });

/** Plan: günlere göre öğünler, "Başka öner", maliyet ve alışveriş listesine aktarma */
export default function MealPlanScreen() {
  const t = useTheme();
  const { id } = useLocalSearchParams<{ id: string }>();
  const planId = Number(id);
  const [plan, setPlan] = useState<MealPlanDetail | null>(null);
  const [includePantry, setIncludePantry] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [changing, setChanging] = useState<number | null>(null);
  const [picker, setPicker] = useState(false);
  const [exporting, setExporting] = useState(false);

  const load = useCallback(() => api.mealPlan(planId, includePantry)
    .then(p => { setPlan(p); setError(null); })
    .catch(e => setError((e as Error).message)), [planId, includePantry]);
  useEffect(() => { load(); }, [load]);

  const days = useMemo(() => {
    const byDay = new Map<number, MealPlanEntry[]>();
    for (const e of plan?.entries || []) byDay.set(e.day_index, [...(byDay.get(e.day_index) || []), e]);
    return Array.from(byDay.entries());
  }, [plan]);

  const suggestAnother = async (entry: MealPlanEntry) => {
    setChanging(entry.id);
    try {
      await api.changeMealEntry(planId, entry.id);
      await load();
    } catch (e) { setError((e as Error).message); } finally { setChanging(null); }
  };

  const exportTo = async (listId: number | null) => {
    setExporting(true);
    try {
      const out = await api.exportMealPlan(planId, { list_id: listId, include_pantry: includePantry });
      setPicker(false);
      const open = () => router.push({ pathname: '/list/[id]', params: { id: String(out.list.id) } });
      if (out.skipped.length) {
        Alert.alert('Listeye aktarıldı', `${out.added} ürün eklendi. Marketlerinizde bulunamadığı için eklenmedi: ${out.skipped.join(', ')}`,
          [{ text: 'Listeyi aç', onPress: open }]);
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
          <Muted>{plan.days} gün · {plan.servings} kişilik · {plan.meal_slots.map(s => MEAL_SLOT_LABELS[s]).join(', ')}</Muted>
          {error && <Text style={{ color: t.danger }}>{error}</Text>}

          {days.map(([day, entries]) => (
            <Card key={day} style={{ gap: 10 }}>
              <Text style={{ color: t.text, fontWeight: '800', textTransform: 'capitalize' }}>{dayLabel(entries[0].date)}</Text>
              {entries.map(e => (
                <View key={e.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                  <Pressable style={{ flex: 1, flexDirection: 'row', alignItems: 'center', gap: 10 }}
                    onPress={() => router.push({ pathname: '/recipe/[id]', params: { id: String(e.recipe.id), servings: String(plan.servings) } })}>
                    <Text style={{ fontSize: 28 }}>{e.recipe.icon ?? '🍽️'}</Text>
                    <View style={{ flex: 1 }}>
                      <Muted>{MEAL_SLOT_LABELS[e.slot]}</Muted>
                      <Text style={{ color: t.text, fontWeight: '600' }}>{e.recipe.name}</Text>
                    </View>
                  </Pressable>
                  <Pressable onPress={() => suggestAnother(e)} disabled={changing != null} hitSlop={6}
                    style={{ paddingHorizontal: 10, paddingVertical: 6, borderRadius: 999, borderWidth: 1, borderColor: t.border }}>
                    {changing === e.id ? <ActivityIndicator color={t.tint} />
                      : <Text style={{ color: t.tint, fontWeight: '600', fontSize: 13 }}>🔄 Başka öner</Text>}
                  </Pressable>
                </View>
              ))}
            </Card>
          ))}

          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
            <Text style={{ color: t.text, flex: 1 }}>Evdekileri de hesapla (tuz, baharat)</Text>
            <Switch value={includePantry} onValueChange={setIncludePantry} trackColor={{ true: t.tint }} />
          </View>

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
