import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import FoodIcon from '@/components/FoodIcon';
import { ActionBar, Button, Card, Muted, useTheme } from '@/components/ui';
import { api, RecipeSummary } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { courseGlyph } from '@/lib/icons';

const minutes = (r: RecipeSummary) => r.prep_minutes + r.cook_minutes;

/** Hızlı ama lezzetli yemekler: plan kurmaz, her seferinde tek bir "restoran tabağı" önerir. */
export default function QuickMealScreen() {
  const t = useTheme();
  const [dishes, setDishes] = useState<RecipeSummary[] | null>(null);
  const { user } = useAuth();
  const [index, setIndex] = useState(0);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.recipes('haftaici')
      .then(list => {
        const mains = list.filter(r => r.course_type === 'ana');
        const pool = mains.length ? mains : list;
        // Her açılışta farklı bir tabakla başla
        const start = pool.length ? Math.floor(Math.random() * pool.length) : 0;
        setDishes([...pool.slice(start), ...pool.slice(0, start)]);
      })
      .catch(() => setDishes([]));
  }, []);

  if (dishes === null) return <SafeAreaView edges={[]} style={{ flex: 1, backgroundColor: t.background }} />;
  const dish = dishes[index % Math.max(dishes.length, 1)];
  const addToList = async () => {
    if (!dish) return;
    if (!user) { router.push('/login'); return; }
    setAdding(true);
    setError(null);
    try {
      const out = await api.exportRecipe(dish.id, { list_name: dish.name });
      router.push({ pathname: '/list/[id]', params: { id: String(out.list.id) } });
    } catch (e) { setError((e as Error).message); } finally { setAdding(false); }
  };
  const open = (r: RecipeSummary) => router.push({ pathname: '/recipe/[id]', params: { id: String(r.id) } });

  return (
    <SafeAreaView edges={[]} style={{ flex: 1, backgroundColor: t.background }}>
      <ScrollView style={{ flex: 1 }}>
        <View style={{ padding: 16, gap: 16 }}>
          <Text style={{ color: t.text, fontWeight: '800', fontSize: 22, letterSpacing: -0.4 }}>Bugünün tabağı</Text>
          <Muted style={{ marginTop: -8 }}>Restoran gibi sofra, market fiyatına. Menü kurmadan tek bir yemek: beğendiysen tarife bak, beğenmediysen başkasını iste.</Muted>
          {!dish ? (
            <Muted>Şu an gösterilecek tabak yok.</Muted>
          ) : (
            <Pressable onPress={() => open(dish)}>
              <Card style={{ gap: 10, padding: 20 }}>
                <View style={{ width: 64, height: 64, borderRadius: 18, backgroundColor: t.tintSoft, alignItems: 'center', justifyContent: 'center' }}>
                  <FoodIcon name={courseGlyph(dish.course_type)} size={34} />
                </View>
                <Text style={{ color: t.text, fontWeight: '800', fontSize: 20 }}>{dish.name}</Text>
                {!!dish.description && <Muted>{dish.description}</Muted>}
                <Muted style={{ fontWeight: '700' }}>
                  {minutes(dish) > 0 ? `${minutes(dish)} dk` : 'Hazır'}
                  {dish.nutrition ? ` · ${dish.nutrition.kcal} kcal` : ''} · {dish.servings} kişilik
                </Muted>
              </Card>
            </Pressable>
          )}
          {dishes.length > 1 && (
            <View style={{ gap: 8 }}>
              <Muted style={{ fontWeight: '700' }}>Diğer tabaklar</Muted>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginHorizontal: -16 }}
                contentContainerStyle={{ paddingHorizontal: 16, gap: 8 }}>
                {dishes.map((r, i) => i === index % dishes.length ? null : (
                  <Pressable key={r.id} onPress={() => setIndex(i)}>
                    <Card style={{ width: 150, gap: 4, padding: 12 }}>
                      <Text style={{ color: t.text, fontWeight: '700' }} numberOfLines={2}>{r.name}</Text>
                      <Muted style={{ fontSize: 12 }}>{minutes(r) > 0 ? `${minutes(r)} dk` : 'Hazır'}</Muted>
                    </Card>
                  </Pressable>
                ))}
              </ScrollView>
            </View>
          )}
        </View>
      </ScrollView>
      {!!dish && (
        <ActionBar>
          {!!error && <Muted style={{ color: t.danger }}>{error}</Muted>}
          <Button title="Malzemeleri alışveriş listesine ekle" onPress={addToList} busy={adding} />
          <Button title="Tarife bak" onPress={() => open(dish)} />
          {dishes.length > 1 && <Button title="Başka tabak öner" onPress={() => setIndex(i => (i + 1) % dishes.length)} />}
        </ActionBar>
      )}
    </SafeAreaView>
  );
}
