import { router } from 'expo-router';
import { memo } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';

import FoodIcon from '@/components/FoodIcon';
import { Card, Chip, Muted, useTheme } from '@/components/ui';
import { COURSE_LABELS, CourseType, Cuisine, RecipeSummary } from '@/lib/api';
import { courseGlyph, cuisineGlyph } from '@/lib/icons';

const COURSE_ORDER: CourseType[] = ['corba', 'ana', 'yan', 'salata', 'tatli', 'icecek', 'ara'];

const RecipeCard = memo(function RecipeCard({ r, showCuisine }: { r: RecipeSummary; showCuisine: boolean }) {
  const t = useTheme();
  return (
    <Pressable onPress={() => router.push({ pathname: '/recipe/[id]', params: { id: String(r.id) } })}>
      <Card style={{ width: 132, gap: 4, padding: 12 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
          <View style={{ width: 42, height: 42, borderRadius: 10, backgroundColor: t.tintSoft, alignItems: 'center', justifyContent: 'center' }}>
            <FoodIcon name={courseGlyph(r.course_type)} size={22} />
          </View>
          {showCuisine && <FoodIcon name={cuisineGlyph(r.cuisine)} size={16} color={t.textMuted} />}
        </View>
        <Text style={{ color: t.text, fontWeight: '700' }} numberOfLines={2}>{r.name}</Text>
        <Muted style={{ fontSize: 13 }}>
          {r.prep_minutes + r.cook_minutes > 0 ? `${r.prep_minutes + r.cook_minutes} dk` : 'Hazır'}
          {r.nutrition ? ` · ${r.nutrition.kcal} kcal` : ''}
        </Muted>
        {(r.liked || r.like_count > 0) && <Muted style={{ fontSize: 13 }}>{r.like_count} beğeni</Muted>}
      </Card>
    </Pressable>
  );
});

/**
 * Yemek Planı ekranının altındaki tarif listesi. Ayrı ve memo'lu: form çiplerine dokunmak (gün, öğün,
 * mutfak…) bu listeyi yeniden çizmez, yalnız tarifler ya da seçili mutfak değişince çizilir.
 */
function RecipeBrowser({ recipes, cuisines, browse, onBrowse }: {
  recipes: RecipeSummary[]; cuisines: Cuisine[]; browse: string | null; onBrowse: (slug: string | null) => void;
}) {
  const t = useTheme();
  if (!recipes.length && !browse) return null;
  return (
    <View style={{ gap: 10 }}>
      <Text style={{ color: t.text, fontWeight: '800', fontSize: 18, letterSpacing: -0.3 }}>Tarifler</Text>
      <Muted style={{ marginTop: -4 }}>En sevilenler önde. Beğendiğiniz tarifi kalp ile işaretleyin; planlarda daha sık önerilir.</Muted>
      {cuisines.length > 1 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginHorizontal: -16 }}
          contentContainerStyle={{ paddingHorizontal: 16, gap: 8 }}>
          <Chip on={browse === null} label="Hepsi" onPress={() => onBrowse(null)} />
          {cuisines.filter(c => c.recipe_count > 0).map(c => (
            <Chip key={c.slug} on={browse === c.slug} label={c.name} onPress={() => onBrowse(c.slug)} />
          ))}
        </ScrollView>
      )}
      {recipes.length === 0 && <Muted>Bu mutfakta seçimlerinize uyan tarif yok.</Muted>}
      {COURSE_ORDER.map(course => {
        const group = recipes.filter(r => r.course_type === course);
        if (!group.length) return null;
        return (
          <View key={course} style={{ gap: 6 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
              <FoodIcon name={courseGlyph(course)} size={16} color={t.textMuted} />
              <Muted style={{ fontWeight: '700' }}>{COURSE_LABELS[course]}</Muted>
            </View>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginHorizontal: -16 }}
              contentContainerStyle={{ paddingHorizontal: 16, gap: 8 }}>
              {group.map(r => <RecipeCard key={r.id} r={r} showCuisine={browse === null} />)}
            </ScrollView>
          </View>
        );
      })}
    </View>
  );
}

export default memo(RecipeBrowser);
