import { Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import MealCostCard from '@/components/MealCostCard';
import { Card, Muted, useTheme } from '@/components/ui';
import { api, MEAL_SLOT_LABELS, RecipeDetail } from '@/lib/api';

/** Tarif: malzemeler, yapılışı ve seçilen kişi sayısına göre maliyet */
export default function RecipeScreen() {
  const t = useTheme();
  const params = useLocalSearchParams<{ id: string; servings?: string }>();
  const [servings, setServings] = useState<number | null>(params.servings ? Number(params.servings) : null);
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.recipe(Number(params.id), servings ?? undefined)
      .then(r => { setRecipe(r); setError(null); })
      .catch(e => setError((e as Error).message));
  }, [params.id, servings]);

  if (!recipe) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: t.background, padding: 16 }}>
        {error ? <Text style={{ color: t.danger }}>{error}</Text> : <ActivityIndicator color={t.tint} />}
      </View>
    );
  }
  const people = servings ?? recipe.servings;
  const scale = people / recipe.servings;

  const step = (delta: number) => setServings(Math.min(12, Math.max(1, people + delta)));
  const round = (btn: string, onPress: () => void) => (
    <Pressable onPress={onPress} hitSlop={8} style={{ width: 34, height: 34, borderRadius: 17, borderWidth: 1, borderColor: t.border, alignItems: 'center', justifyContent: 'center' }}>
      <Text style={{ color: t.text, fontSize: 18 }}>{btn}</Text>
    </Pressable>
  );

  return (
    <SafeAreaView edges={[]} style={{ flex: 1, backgroundColor: t.background }}>
      <Stack.Screen options={{ title: recipe.name }} />
      <ScrollView>
        <View style={{ padding: 16, gap: 16 }}>
          <View style={{ alignItems: 'center', gap: 6 }}>
            <Text style={{ fontSize: 64 }}>{recipe.icon ?? '🍽️'}</Text>
            <Text style={{ color: t.text, fontSize: 24, fontWeight: '800' }}>{recipe.name}</Text>
            <Muted style={{ textAlign: 'center' }}>{recipe.description}</Muted>
            <Muted>
              {recipe.course} · Hazırlık {recipe.prep_minutes} dk · Pişirme {recipe.cook_minutes} dk · {recipe.meal_slots.map(s => MEAL_SLOT_LABELS[s]).join(', ')}
            </Muted>
          </View>

          <Card style={{ gap: 10 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
              <Text style={{ color: t.text, fontWeight: '800', fontSize: 17, flex: 1 }}>Malzemeler</Text>
              {round('−', () => step(-1))}
              <Text style={{ color: t.text, fontWeight: '700' }}>{people} kişilik</Text>
              {round('+', () => step(1))}
            </View>
            {scale !== 1 && <Muted>Ölçüler {recipe.servings} kişiliktir; maliyet {people} kişiye göre hesaplandı.</Muted>}
            {recipe.ingredients.map(i => (
              <View key={i.name} style={{ flexDirection: 'row', gap: 8 }}>
                <Text style={{ color: t.text, flex: 1 }}>• {i.name}{i.is_pantry ? ' (evde)' : ''}</Text>
                <Muted>{i.amount_text}</Muted>
              </View>
            ))}
          </Card>

          <Card style={{ gap: 10 }}>
            <Text style={{ color: t.text, fontWeight: '800', fontSize: 17 }}>Yapılışı</Text>
            {recipe.steps.map((s, i) => (
              <View key={i} style={{ flexDirection: 'row', gap: 10 }}>
                <Text style={{ color: t.tint, fontWeight: '800', width: 20 }}>{i + 1}.</Text>
                <Text style={{ color: t.text, flex: 1, lineHeight: 20 }}>{s}</Text>
              </View>
            ))}
          </Card>

          <MealCostCard cost={recipe.cost} title={`${people} kişilik maliyet`} />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
