import { router } from 'expo-router';
import { ReactNode } from 'react';
import {
  ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, TextInputProps, View, ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';

export function useTheme() {
  return Colors[useColorScheme()];
}

/** Sekme ekranlarının kabuğu: güvenli alan + kaydırma + sayfa arka planı */
export function Screen({ children, scroll = true }: { children: ReactNode; scroll?: boolean }) {
  const t = useTheme();
  const body = <View style={styles.body}>{children}</View>;
  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: t.background }}>
      {scroll ? <ScrollView keyboardShouldPersistTaps="handled">{body}</ScrollView> : body}
    </SafeAreaView>
  );
}

export function Title({ children }: { children: ReactNode }) {
  const t = useTheme();
  return <Text style={[styles.title, { color: t.text }]}>{children}</Text>;
}

export function Muted({ children, style }: { children: ReactNode; style?: object }) {
  const t = useTheme();
  return <Text style={[{ color: t.textMuted, fontSize: 13 }, style]}>{children}</Text>;
}

export function Card({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  const t = useTheme();
  return <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }, style]}>{children}</View>;
}

export function Button({
  title, onPress, busy, kind = 'primary', disabled,
}: { title: string; onPress: () => void; busy?: boolean; kind?: 'primary' | 'secondary'; disabled?: boolean }) {
  const t = useTheme();
  const primary = kind === 'primary';
  return (
    <Pressable onPress={onPress} disabled={busy || disabled} accessibilityRole="button"
      style={({ pressed }) => [styles.button, {
        backgroundColor: primary ? t.tint : t.card, borderColor: primary ? t.tint : t.border,
        opacity: pressed || busy || disabled ? 0.6 : 1,
      }]}>
      {busy ? <ActivityIndicator color={primary ? '#fff' : t.tint} />
        : <Text style={{ color: primary ? '#fff' : t.text, fontWeight: '600', fontSize: 16 }}>{title}</Text>}
    </Pressable>
  );
}

export function Input(props: TextInputProps) {
  const t = useTheme();
  return (
    <TextInput placeholderTextColor={t.textMuted} {...props}
      style={[styles.input, { color: t.text, backgroundColor: t.card, borderColor: t.border }, props.style]} />
  );
}

/** Üyelik gerektiren sekmelerde giriş yapılmamışsa gösterilir */
export function LoginPrompt({ what }: { what: string }) {
  return (
    <Card style={{ alignItems: 'center', gap: 12, paddingVertical: 28 }}>
      <Text style={{ fontSize: 36 }}>🔐</Text>
      <Muted style={{ textAlign: 'center' }}>{what} için giriş yapın ya da ücretsiz üye olun.</Muted>
      <Button title="Giriş yap / Üye ol" onPress={() => router.push('/login')} />
    </Card>
  );
}

const styles = StyleSheet.create({
  body: { padding: 16, gap: 16 },
  title: { fontSize: 26, fontWeight: '800' },
  card: { borderRadius: 16, borderWidth: 1, padding: 16 },
  button: { borderRadius: 14, borderWidth: 1, paddingVertical: 14, paddingHorizontal: 20, alignItems: 'center' },
  input: { borderRadius: 12, borderWidth: 1, paddingHorizontal: 14, paddingVertical: 12, fontSize: 16 },
});
