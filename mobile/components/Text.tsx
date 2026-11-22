import { StyleSheet, Text as RNText, TextProps } from 'react-native';

import { NEW_LOOK } from '@/constants/Look';
import { useFontScale } from '@/lib/fontScale';

/** fontWeight'e göre DM Sans ailesi seçer (özel yazı tiplerinde fontWeight tek başına çalışmaz). */
export function fontFor(weight?: string | number): string {
  const w = String(weight ?? '400');
  if (w === 'bold' || ['600', '700', '800', '900'].includes(w)) return 'DMSans_700Bold';
  if (w === '500') return 'DMSans_500Medium';
  return 'DMSans_400Regular';
}

/** react-native Text yerine kullanılır; NEW_LOOK kapalıysa sistem yazı tipi kalır. */
export function Text({ style, ...rest }: TextProps) {
  const { scale } = useFontScale();
  const flat = StyleSheet.flatten(style) || {};
  // Uygulama içi "Yazı boyutu" ayarı: yazı ve satır yüksekliği birlikte büyür
  const scaled = scale !== 1 && typeof flat.fontSize === 'number'
    ? { fontSize: Math.round(flat.fontSize * scale), ...(typeof flat.lineHeight === 'number' ? { lineHeight: Math.round(flat.lineHeight * scale) } : {}) }
    : null;
  if (!NEW_LOOK || flat.fontFamily) return <RNText style={scaled ? [style, scaled] : style} {...rest} />;
  return <RNText style={[style, scaled, { fontFamily: fontFor(flat.fontWeight), fontWeight: undefined }]} {...rest} />;
}
