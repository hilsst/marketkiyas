import { router } from 'expo-router';
import { Pressable, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import Icon, { IconName } from '@/components/Icon';
import { Muted, useTheme } from '@/components/ui';
import { useAuth } from '@/lib/auth';

/** Karşılama: uygulama açılınca iki seçenek, Yemek Planı ya da Alışveriş */
export default function WelcomeScreen() {
  const t = useTheme();
  const { user } = useAuth();
  const name = user?.full_name?.split(' ')[0];

  const option = (icon: IconName, title: string, text: string, onPress: () => void, primary: boolean) => (
    <Pressable onPress={onPress} accessibilityRole="button"
      style={({ pressed }) => ({
        borderRadius: 24, padding: primary ? 24 : 18, gap: 8, opacity: pressed ? 0.88 : 1, overflow: 'hidden',
        flexDirection: primary ? 'column' : 'row', alignItems: primary ? 'stretch' : 'center',
        backgroundColor: primary ? t.tint : t.card, shadowColor: t.shadow, shadowOpacity: primary ? 0 : 0.07,
        shadowRadius: 14, shadowOffset: { width: 0, height: 4 }, elevation: primary ? 0 : 2,
      })}>
      {primary ? (
        <>
          <Icon name={icon} size={34} color="#fff" />
          <Text style={{ color: '#fff', fontSize: 15, fontWeight: '600', opacity: 0.9 }}>Ne pişireceğini seç, gerisini Ucuzu en ucuza yapsın</Text>
          <Text style={{ color: '#fff', fontSize: 28, fontWeight: '800', letterSpacing: -0.5 }}>{title}</Text>
          <Text style={{ color: '#fff', fontSize: 14, opacity: 0.9 }}>{text}</Text>
        </>
      ) : (
        <>
          <View style={{ width: 48, height: 48, borderRadius: 16, backgroundColor: t.tintSoft, alignItems: 'center', justifyContent: 'center' }}>
            <Icon name={icon} size={24} color={t.tint} />
          </View>
          <View style={{ flex: 1, gap: 2 }}>
            <Text style={{ color: t.text, fontSize: 18, fontWeight: '800' }}>{title}</Text>
            <Text style={{ color: t.textMuted, fontSize: 14 }}>{text}</Text>
          </View>
          <Icon name="chevron-right" size={20} color={t.textMuted} />
        </>
      )}
    </Pressable>
  );

  // Alışveriş: ana sayfaya (sekmeler) dön; Yemek Planı: planlayıcıyı aç
  const shopping = () => (router.canGoBack() ? router.back() : router.replace('/'));
  const meals = () => router.replace('/meals');

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.background }}>
      <View style={{ flex: 1, padding: 20, gap: 14, justifyContent: 'center' }}>
        <View style={{ gap: 4, marginBottom: 10 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
            <View style={{ width: 42, height: 42, borderRadius: 14, backgroundColor: t.tint, alignItems: 'center', justifyContent: 'center' }}>
              <Icon name="shopping-cart" size={22} color="#fff" />
            </View>
            <Text style={{ color: t.text, fontSize: 26, fontWeight: '800', letterSpacing: -0.5 }}>Ucuzu</Text>
          </View>
          <Text style={{ color: t.text, fontSize: 22, fontWeight: '700', marginTop: 18 }}>{name ? `Hoş geldin ${name}!` : 'Hoş geldin!'}</Text>
          <Muted style={{ fontSize: 15 }}>Bugün ne yapmak istersin?</Muted>
        </View>
        {option('coffee', 'Yemek Planı', '1-14 günlük menü: bütçene, dolabındakilere göre; artan yemeği yarına sakla. Maliyetini gör, alışveriş listene aktar.', meals, true)}
        {option('shopping-bag', 'Alışveriş', 'Ürün ara, fiyatları karşılaştır, listeni en ucuz marketlere göre planla.', shopping, false)}
        {!user && <Muted style={{ textAlign: 'center', marginTop: 6 }}>Üye olmadan başlayabilirsin</Muted>}
      </View>
    </SafeAreaView>
  );
}
