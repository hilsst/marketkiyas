import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { courseGlyph } from '@/lib/icons';
import FoodIcon from '@/components/FoodIcon';
import MealCostCard from '@/components/MealCostCard';
import NutritionCard from '@/components/NutritionCard';
import AddRecipeToList from '@/components/AddRecipeToList';
import { ActionBar, Button, Card, Muted, useTheme } from '@/components/ui';
import { ALLERGEN_LABELS, api, DIET_LABELS, MEAL_SLOT_LABELS, RecipeDetail } from '@/lib/api';
import { scaleAmount } from '@/lib/amount';
import { useAuth } from '@/lib/auth';

/** Tarif: malzemeler, yapılışı ve seçilen kişi sayısına göre maliyet */
export default function RecipeScreen() {
  const t = useTheme();
  const params = useLocalSearchParams<{ id: string; servings?: string }>();
  const [servings, setServings] = useState<number | null>(params.servings ? Number(params.servings) : null);
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth();

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

  const toggleLike = async () => {
    if (!user) { setError('Beğenmek için giriş yapın.'); return; }
    const like = !recipe.liked;
    setRecipe({ ...recipe, liked: like, like_count: recipe.like_count + (like ? 1 : -1) });
    try { await api.likeRecipe(recipe.id, like); } catch (e) {
      setRecipe(recipe);
      setError((e as Error).message);
    }
  };
  const badge = (key: string, label: string, color: string) => (
    <View key={key} style={{ paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999, borderWidth: 1, borderColor: color }}>
      <Text style={{ color, fontSize: 12, fontWeight: '700' }}>{label}</Text>
    </View>
  );

  const step = (delta: number) => setServings(Math.min(12, Math.max(1, people + delta)));
  const round = (btn: string, onPress: () => void) => (
    <Pressable onPress={onPress} hitSlop={8} style={{ width: 38, height: 38, borderRadius: 19, borderWidth: 1.5, borderColor: t.border, alignItems: 'center', justifyContent: 'center' }}>
      <Text style={{ color: t.text, fontSize: 18 }}>{btn}</Text>
    </Pressable>
  );

  return (
    <SafeAreaView edges={[]} style={{ flex: 1, backgroundColor: t.background }}>
      <Stack.Screen options={{ title: recipe.name }} />
      <ScrollView style={{ flex: 1 }}>
        <View style={{ padding: 16, gap: 16 }}>
          <View style={{ alignItems: 'center', gap: 6 }}>
            <View style={{ width: 120, height: 120, borderRadius: 60, backgroundColor: t.tintSoft, alignItems: 'center', justifyContent: 'center' }}>
              <FoodIcon name={courseGlyph(recipe.course_type)} size={60} />
            </View>
            <Text style={{ color: t.text, fontSize: 26, fontWeight: '800', letterSpacing: -0.5, marginTop: 6 }}>{recipe.name}</Text>
            <Muted style={{ textAlign: 'center' }}>{recipe.description}</Muted>
            <Muted>
              {recipe.course} · Hazırlık {recipe.prep_minutes} dk · Pişirme {recipe.cook_minutes} dk · {recipe.meal_slots.map(s => MEAL_SLOT_LABELS[s]).join(', ')}
            </Muted>
            <Pressable onPress={toggleLike} hitSlop={8} accessibilityLabel={recipe.liked ? 'Beğenmekten vazgeç' : 'Beğen'}
              style={{ flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 999,
                borderWidth: 1, borderColor: recipe.liked ? t.danger : t.border }}>
              <FoodIcon name={recipe.liked ? 'heart' : 'heart-outline'} size={18} color={recipe.liked ? t.danger : t.textMuted} />
              <Text style={{ color: t.text, fontWeight: '700' }}>{recipe.liked ? 'Beğendin' : 'Beğen'} · {recipe.like_count}</Text>
            </Pressable>
            {error && <Text style={{ color: t.danger }}>{error}</Text>}
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: 6 }}>
              {recipe.diets.map(d => badge(d, DIET_LABELS[d], t.tint))}
              {recipe.allergens.map(a => badge(a, `İçerir: ${ALLERGEN_LABELS[a]}`, t.danger))}
            </View>
          </View>

          {recipe.nutrition && <NutritionCard nutrition={recipe.nutrition} title="Besin değeri (1 porsiyon)" />}

          <Card style={{ gap: 10 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
              <Text style={{ color: t.text, fontWeight: '800', fontSize: 17, flex: 1 }}>Malzemeler</Text>
              {round('−', () => step(-1))}
              <Text style={{ color: t.text, fontWeight: '700' }}>{people} kişilik</Text>
              {round('+', () => step(1))}
            </View>
            {scale !== 1 && <Muted>Ölçüler ve maliyet {people} kişiye göre hesaplandı (tarif {recipe.servings} kişilik).</Muted>}
            {recipe.ingredients.map(i => (
              <View key={i.name} style={{ flexDirection: 'row', gap: 8 }}>
                <Text style={{ color: t.text, flex: 1 }}>• {i.name}{i.is_pantry ? ' (evde)' : ''}</Text>
                <Muted>{scaleAmount(i.amount_text, scale)}</Muted>
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
      <ActionBar>
        <AddRecipeToList recipeId={recipe.id} servings={people} kind={recipe.steps.length > 0 ? 'secondary' : undefined} />
        {recipe.steps.length > 0 && (
          <Button title="Pişirme modunu başlat"
            onPress={() => router.push({ pathname: '/cook/[id]', params: { id: String(recipe.id), servings: String(people) } })} />
        )}
      </ActionBar>
    </SafeAreaView>
  );
}
