import type { ComponentProps } from 'react';
import type { MaterialCommunityIcons } from '@expo/vector-icons';

export type FoodGlyph = ComponentProps<typeof MaterialCommunityIcons>['name'];

/** Sunucudaki emoji verisi yerine vektör simge: kategori slug'ından simge adı */
const CATEGORY: Record<string, FoodGlyph> = {
  'sut-kahvaltilik': 'cow', 'meyve-sebze': 'food-apple', 'et-tavuk-balik': 'food-drumstick', 'temel-gida': 'pasta',
  atistirmalik: 'cookie', icecek: 'cup', firin: 'bread-slice', dondurulmus: 'snowflake', temizlik: 'spray-bottle',
  'kisisel-bakim': 'lotion', bebek: 'baby-bottle',
};
export const categoryGlyph = (slug?: string | null): FoodGlyph => (slug && CATEGORY[slug]) || 'shopping';

const COURSE: Record<string, FoodGlyph> = {
  corba: 'pot-steam', ana: 'silverware-fork-knife', yan: 'rice', salata: 'leaf', tatli: 'cake-variant', icecek: 'cup', ara: 'food-apple',
};
export const courseGlyph = (course?: string | null): FoodGlyph => (course && COURSE[course]) || 'silverware-fork-knife';

const CUISINE: Record<string, FoodGlyph> = { anadolu: 'pot-steam', italyan: 'pasta', uzakdogu: 'noodles', meksika: 'taco' };
export const cuisineGlyph = (slug?: string | null): FoodGlyph => (slug && CUISINE[slug]) || 'earth';
