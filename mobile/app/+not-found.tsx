import { Link, Stack } from 'expo-router';
import { Text } from 'react-native';

import { Muted, Screen, useTheme } from '@/components/ui';

export default function NotFoundScreen() {
  const t = useTheme();
  return (
    <>
      <Stack.Screen options={{ title: 'Bulunamadı' }} />
      <Screen>
        <Muted>Bu sayfa yok.</Muted>
        <Link href="/"><Text style={{ color: t.tint, fontWeight: '600' }}>Ana sayfaya dön</Text></Link>
      </Screen>
    </>
  );
}
