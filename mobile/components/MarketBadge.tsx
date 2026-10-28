import { Text, View } from 'react-native';

import { useCatalog } from '@/lib/catalog';

// Web arayüzündeki rozetlerle aynı renk ve kısa adlar (frontend/src/components/MarketLogo.tsx)
const COLORS: Record<string, string> = {
  bim: '#dc2626', a101: '#0284c7', sok: '#ea580c', file: '#4338ca',
  migros: '#f97316', carrefour: '#1e40af', tarim_kredi: '#16a34a', hakmar: '#b91c1c',
};
const LABELS: Record<string, string> = {
  bim: 'BİM', a101: 'A101', sok: 'ŞOK', file: 'File', migros: 'M', carrefour: 'CSA', tarim_kredi: 'TK', hakmar: 'H',
};

export default function MarketBadge({ id, size = 28 }: { id: number | null | undefined; size?: number }) {
  const m = useCatalog().marketById(id);
  const label = m ? LABELS[m.slug] || m.name[0] : '?';
  return (
    <View accessibilityLabel={m?.name} style={{
      width: size, height: size, borderRadius: size / 2, alignItems: 'center', justifyContent: 'center',
      backgroundColor: (m && (COLORS[m.slug] || m.color)) || '#9ca3af',
    }}>
      <Text style={{ color: '#fff', fontWeight: '800', fontSize: size * (label.length > 2 ? 0.3 : 0.42) }}>{label}</Text>
    </View>
  );
}
