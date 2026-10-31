import { router } from 'expo-router';
import { Pressable, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Muted, useTheme } from '@/components/ui';
import { useAuth } from '@/lib/auth';

/** Karşılama: uygulama açılınca iki seçenek, Yemek Planı ya da Alışveriş */
export default function WelcomeScreen() {
  const t = useTheme();
  const { user } = useAuth();
  const name = user?.full_name?.split(' ')[0];

  const option = (icon: string, title: string, text: string, onPress: () => void, primary: boolean) => (
    <Pressable onPress={onPress} accessibilityRole="button"
      style={({ pressed }) => ({
        borderRadius: 24, padding: 24, gap: 8, opacity: pressed ? 0.85 : 1,
        backgroundColor: primary ? t.tint : t.card, borderWidth: 1, borderColor: primary ? t.tint : t.border,
      })}>
      <Text style={{ fontSize: 48 }}>{icon}</Text>
      <Text style={{ color: primary ? '#fff' : t.text, fontSize: 26, fontWeight: '900' }}>{title}</Text>
      <Text style={{ color: primary ? '#fff' : t.textMuted, fontSize: 15, opacity: primary ? 0.9 : 1 }}>{text}</Text>
    </Pressable>
  );

  // Alışveriş: ana sayfaya (sekmeler) dön; Yemek Planı: planlayıcıyı aç
  const shopping = () => (router.canGoBack() ? router.back() : router.replace('/'));
  const meals = () => router.replace('/meals');

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.background }}>
      <View style={{ flex: 1, padding: 20, gap: 16, justifyContent: 'center' }}>
        <View style={{ gap: 6, marginBottom: 8 }}>
          <Text style={{ color: t.text, fontSize: 34, fontWeight: '900' }}>🛒 Ucuzu</Text>
          <Text style={{ color: t.text, fontSize: 20, fontWeight: '700' }}>{name ? `Hoş geldin ${name}!` : 'Hoş geldin!'}</Text>
          <Muted style={{ fontSize: 15 }}>Bugün ne yapmak istersin?</Muted>
        </View>
        {option('🍲', 'Yemek Planı', '1-14 günlük menü: bütçene, dolabındakilere göre; artan yemeği yarına sakla. Maliyetini gör, alışveriş listene aktar.', meals, true)}
        {option('🛍️', 'Alışveriş', 'Ürün ara, fiyatları karşılaştır, listeni en ucuz marketlere göre planla.', shopping, false)}
      </View>
    </SafeAreaView>
  );
}
