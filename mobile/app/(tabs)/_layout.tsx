import { Tabs } from 'expo-router';
import { Text } from 'react-native';

import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';

// Web arayüzündeki alt menüyle aynı sekmeler ve simgeler
function TabIcon({ glyph, focused }: { glyph: string; focused: boolean }) {
  return <Text style={{ fontSize: 22, opacity: focused ? 1 : 0.55 }}>{glyph}</Text>;
}
const icon = (glyph: string) => function Icon({ focused }: { focused: boolean }) {
  return <TabIcon glyph={glyph} focused={focused} />;
};

export default function TabLayout() {
  const colorScheme = useColorScheme();

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: Colors[colorScheme].tint,
        // Her ekran kendi başlığını çizer
        headerShown: false,
      }}>
      <Tabs.Screen name="index" options={{ title: 'Ana Sayfa', tabBarIcon: icon('🏠') }} />
      <Tabs.Screen name="deals" options={{ title: 'Fırsatlar', tabBarIcon: icon('🏷️') }} />
      <Tabs.Screen name="lists" options={{ title: 'Listeler', tabBarIcon: icon('📋') }} />
      <Tabs.Screen name="alerts" options={{ title: 'Alarmlar', tabBarIcon: icon('🔔') }} />
      <Tabs.Screen name="profile" options={{ title: 'Profil', tabBarIcon: icon('👤') }} />
    </Tabs>
  );
}
