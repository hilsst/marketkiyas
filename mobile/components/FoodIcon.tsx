import { MaterialCommunityIcons } from '@expo/vector-icons';

import { useTheme } from '@/components/ui';
import type { FoodGlyph } from '@/lib/icons';

/** Yiyecek/kategori vektör simgesi (MaterialCommunityIcons) */
export default function FoodIcon({ name, size = 24, color }: { name: FoodGlyph; size?: number; color?: string }) {
  const t = useTheme();
  return <MaterialCommunityIcons name={name} size={size} color={color ?? t.tint} />;
}
