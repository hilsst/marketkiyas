import { Tabs } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import Icon, { IconName } from '@/components/Icon';
import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';

const icon = (name: IconName) => function TabIcon({ color }: { color: unknown }) {
  return <Icon name={name} size={24} color={color as string} />;
};

export default function TabLayout() {
  const colorScheme = useColorScheme();
  const c = Colors[colorScheme];
  const insets = useSafeAreaInsets();

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: c.tabIconSelected,
        tabBarInactiveTintColor: c.tabIconDefault,
        tabBarLabelStyle: { fontSize: 12, fontWeight: '700', lineHeight: 16 },
        // Sabit yükseklik gezinme çubuğu payını yutuyordu: alt boşluğu cihazdan alıyoruz
        tabBarStyle: { backgroundColor: c.card, borderTopColor: c.border, height: 68 + insets.bottom, paddingTop: 8, paddingBottom: 6 + insets.bottom },
        // Her ekran kendi başlığını çizer
        headerShown: false,
      }}>
      <Tabs.Screen name="index" options={{ title: 'Ana Sayfa', tabBarIcon: icon('home') }} />
      <Tabs.Screen name="deals" options={{ title: 'Fırsatlar', tabBarIcon: icon('tag') }} />
      <Tabs.Screen name="lists" options={{ title: 'Listeler', tabBarIcon: icon('list') }} />
      <Tabs.Screen name="alerts" options={{ title: 'Takip', tabBarIcon: icon('bell') }} />
      <Tabs.Screen name="profile" options={{ title: 'Profil', tabBarIcon: icon('user') }} />
    </Tabs>
  );
}
