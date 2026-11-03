import { Tabs } from 'expo-router';

import Icon, { IconName } from '@/components/Icon';
import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';

const icon = (name: IconName) => function TabIcon({ color }: { color: unknown }) {
  return <Icon name={name} size={24} color={color as string} />;
};

export default function TabLayout() {
  const colorScheme = useColorScheme();
  const c = Colors[colorScheme];

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: c.tabIconSelected,
        tabBarInactiveTintColor: c.tabIconDefault,
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600', lineHeight: 15 },
        tabBarStyle: { backgroundColor: c.card, borderTopColor: c.border, height: 72, paddingTop: 8, paddingBottom: 10 },
        // Her ekran kendi başlığını çizer
        headerShown: false,
      }}>
      <Tabs.Screen name="index" options={{ title: 'Ana Sayfa', tabBarIcon: icon('home') }} />
      <Tabs.Screen name="deals" options={{ title: 'Fırsatlar', tabBarIcon: icon('tag') }} />
      <Tabs.Screen name="lists" options={{ title: 'Listeler', tabBarIcon: icon('list') }} />
      <Tabs.Screen name="alerts" options={{ title: 'Alarmlar', tabBarIcon: icon('bell') }} />
      <Tabs.Screen name="profile" options={{ title: 'Profil', tabBarIcon: icon('user') }} />
    </Tabs>
  );
}
