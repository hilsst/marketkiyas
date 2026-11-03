import { Feather } from '@expo/vector-icons';
import { ComponentProps } from 'react';

import { useTheme } from '@/components/ui';

export type IconName = ComponentProps<typeof Feather>['name'];

/** Tek çizgi stilinde vektör simge (emoji yerine: cihazdan bağımsız, tema rengini alır) */
export default function Icon({ name, size = 22, color }: { name: IconName; size?: number; color?: string }) {
  const t = useTheme();
  return <Feather name={name} size={size} color={color ?? t.text} />;
}
