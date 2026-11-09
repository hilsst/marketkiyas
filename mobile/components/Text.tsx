import { StyleSheet, Text as RNText, TextProps } from 'react-native';

import { NEW_LOOK } from '@/constants/Look';

/** fontWeight'e göre DM Sans ailesi seçer (özel yazı tiplerinde fontWeight tek başına çalışmaz). */
export function fontFor(weight?: string | number): string {
  const w = String(weight ?? '400');
  if (w === 'bold' || ['600', '700', '800', '900'].includes(w)) return 'DMSans_700Bold';
  if (w === '500') return 'DMSans_500Medium';
  return 'DMSans_400Regular';
}

/** react-native Text yerine kullanılır; NEW_LOOK kapalıysa sistem yazı tipi kalır. */
export function Text({ style, ...rest }: TextProps) {
  if (!NEW_LOOK) return <RNText style={style} {...rest} />;
  const flat = StyleSheet.flatten(style) || {};
  if (flat.fontFamily) return <RNText style={style} {...rest} />;
  return <RNText style={[style, { fontFamily: fontFor(flat.fontWeight), fontWeight: undefined }]} {...rest} />;
}
