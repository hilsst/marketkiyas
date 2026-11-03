import { router } from 'expo-router';
import { ReactNode } from 'react';
import {
  ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, TextInputProps, View, ViewStyle,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';

import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';
import Icon, { IconName } from '@/components/Icon';

export function useTheme() {
  return Colors[useColorScheme()];
}

/** Ekran kabuğu: güvenli alan + kaydırma + sayfa arka planı. Başlık çubuğu olan (yığındaki) ekranlarda safeTop={false} */
export function Screen({ children, scroll = true, safeTop = true, footer }: {
  children: ReactNode; scroll?: boolean; safeTop?: boolean; footer?: ReactNode;
}) {
  const t = useTheme();
  const body = <View style={styles.body}>{children}</View>;
  return (
    <SafeAreaView edges={safeTop ? ['top'] : []} style={{ flex: 1, backgroundColor: t.background }}>
      {scroll ? <ScrollView style={{ flex: 1 }} keyboardShouldPersistTaps="handled">{body}</ScrollView> : body}
      {footer}
    </SafeAreaView>
  );
}

/**
 * Ekranın altında sabit duran onay çubuğu: liste kendi alanında kayar, butonlar yerinde kalır.
 * Android gezinme çubuğunun (ve iPhone alt çizgisinin) altına girmez.
 */
export function ActionBar({ children }: { children: ReactNode }) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <View style={{
      backgroundColor: t.card, paddingHorizontal: 16, paddingTop: 12, paddingBottom: 12 + insets.bottom, gap: 8,
      borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: t.border,
      shadowColor: t.shadow, shadowOpacity: 0.1, shadowRadius: 12, shadowOffset: { width: 0, height: -4 }, elevation: 8,
    }}>
      {children}
    </View>
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
  return (
    <View style={[styles.card, { backgroundColor: t.card, shadowColor: t.shadow }, style]}>{children}</View>
  );
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
        : <Text style={{ color: primary ? '#fff' : t.text, fontWeight: '700', fontSize: 16 }}>{title}</Text>}
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
  const t = useTheme();
  return (
    <Card style={{ alignItems: 'center', gap: 12, paddingVertical: 28 }}>
      <Icon name="lock" size={34} color={t.tint} />
      <Muted style={{ textAlign: 'center' }}>{what} için giriş yapın ya da ücretsiz üye olun.</Muted>
      <Button title="Giriş yap / Üye ol" onPress={() => router.push('/login')} />
    </Card>
  );
}

/** Bölüm başlığı + isteğe bağlı sağ bağlantı ("Tümü") */
export function SectionHeader({ title, action, onAction }: { title: string; action?: string; onAction?: () => void }) {
  const t = useTheme();
  return (
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' }}>
      <Text style={{ color: t.text, fontWeight: '800', fontSize: 18, letterSpacing: -0.3 }}>{title}</Text>
      {action && <Text onPress={onAction} style={{ color: t.tint, fontWeight: '700', fontSize: 14 }}>{action}</Text>}
    </View>
  );
}

/** Seçilebilir hap: seçiliyken koyu zemin */
export function Chip({ label, on, onPress }: { label: string; on?: boolean; onPress?: () => void }) {
  const t = useTheme();
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityState={{ selected: !!on }}
      style={{ paddingHorizontal: 14, paddingVertical: 9, borderRadius: 999, backgroundColor: on ? t.text : t.card,
        borderWidth: 1, borderColor: on ? t.text : t.border }}>
      <Text style={{ color: on ? t.background : t.text, fontWeight: '600', fontSize: 13 }}>{label}</Text>
    </Pressable>
  );
}

/** Üçlü/ikili sekme çubuğu (Ürünler | Fiyatlar, Tek market | Kombinasyon | Fırsatçı) */
export function Segmented<K extends string>({ options, value, onChange }: {
  options: { key: K; label: string }[]; value: K; onChange: (k: K) => void;
}) {
  const t = useTheme();
  return (
    <View style={{ flexDirection: 'row', backgroundColor: t.border, borderRadius: 14, padding: 4 }}>
      {options.map(o => (
        <Pressable key={o.key} onPress={() => onChange(o.key)} accessibilityRole="button"
          style={{ flex: 1, paddingVertical: 10, paddingHorizontal: 2, borderRadius: 11, alignItems: 'center', backgroundColor: value === o.key ? t.card : 'transparent' }}>
          <Text numberOfLines={1} style={{ color: value === o.key ? t.tintDark : t.textMuted, fontWeight: '700', fontSize: options.length > 3 ? 12 : 13 }}>{o.label}</Text>
        </Pressable>
      ))}
    </View>
  );
}

/** Boş durum: büyük simge, tek cümle, en çok iki net buton */
export function EmptyState({ icon, title, text, primary, secondary }: {
  icon: IconName; title: string; text?: string;
  primary?: { title: string; onPress: () => void }; secondary?: { title: string; onPress: () => void };
}) {
  const t = useTheme();
  return (
    <View style={{ alignItems: 'center', gap: 10, paddingVertical: 32 }}>
      <View style={{ width: 112, height: 112, borderRadius: 56, backgroundColor: t.tintSoft, alignItems: 'center', justifyContent: 'center' }}>
        <Icon name={icon} size={48} color={t.tint} />
      </View>
      <Text style={{ color: t.text, fontWeight: '800', fontSize: 20, marginTop: 8 }}>{title}</Text>
      {text && <Muted style={{ textAlign: 'center', maxWidth: 280, fontSize: 14 }}>{text}</Muted>}
      <View style={{ alignSelf: 'stretch', gap: 10, marginTop: 12 }}>
        {primary && <Button title={primary.title} onPress={primary.onPress} />}
        {secondary && <Button title={secondary.title} kind="secondary" onPress={secondary.onPress} />}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  body: { padding: 18, gap: 16 },
  title: { fontSize: 28, fontWeight: '800', letterSpacing: -0.5 },
  card: { borderRadius: 20, padding: 16, shadowOpacity: 0.07, shadowRadius: 14, shadowOffset: { width: 0, height: 4 }, elevation: 2 },
  button: { borderRadius: 16, borderWidth: 1, paddingVertical: 16, paddingHorizontal: 20, alignItems: 'center', minHeight: 52 },
  input: { borderRadius: 14, borderWidth: 1, paddingHorizontal: 14, paddingVertical: 12, fontSize: 16 },
});
