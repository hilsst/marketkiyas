import { router } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, Text } from 'react-native';

import { Button, Input, Muted, useTheme } from '@/components/ui';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';

/** Şifre sıfırlama: e-postaya 6 haneli kod gelir, kod + yeni şifre ile oturum açılır */
export default function ForgotPasswordScreen() {
  const t = useTheme();
  const { startSession } = useAuth();
  const [step, setStep] = useState<'email' | 'code'>('email');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendCode = async () => {
    setError(null);
    if (!email.trim()) { setError('E-posta adresinizi girin.'); return; }
    setBusy(true);
    try {
      await api.requestPasswordReset(email.trim());
      setStep('code');
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  const confirm = async () => {
    setError(null);
    if (!/^\d{6}$/.test(code.trim()) || password.length < 8) {
      setError('6 haneli kodu ve en az 8 karakterli yeni şifreyi girin.');
      return;
    }
    setBusy(true);
    try {
      await startSession(await api.confirmPasswordReset(email.trim(), code.trim(), password));
      router.dismissAll();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1, backgroundColor: t.background }}>
      <ScrollView contentContainerStyle={{ padding: 20, gap: 14 }} keyboardShouldPersistTaps="handled">
        {step === 'email' ? (
          <>
            <Muted>Hesabınızın e-posta adresini yazın, şifre sıfırlama kodunu gönderelim.</Muted>
            <Input placeholder="E-posta" value={email} onChangeText={setEmail} autoCapitalize="none"
              keyboardType="email-address" autoComplete="email" onSubmitEditing={sendCode} />
            {error && <Text style={{ color: t.danger }}>{error}</Text>}
            <Button title="Kod gönder" onPress={sendCode} busy={busy} />
          </>
        ) : (
          <>
            <Muted>{email} adresine bir kod gönderdik (kayıtlı bir hesapsa). Kod 1 saat geçerli; gelmediyse istenmeyen e-postalara bakın.</Muted>
            <Input placeholder="6 haneli kod" value={code} onChangeText={setCode} keyboardType="number-pad"
              maxLength={6} autoComplete="one-time-code" textContentType="oneTimeCode" />
            <Input placeholder="Yeni şifre (en az 8 karakter)" value={password} onChangeText={setPassword}
              secureTextEntry autoComplete="new-password" onSubmitEditing={confirm} />
            {error && <Text style={{ color: t.danger }}>{error}</Text>}
            <Button title="Şifreyi değiştir ve giriş yap" onPress={confirm} busy={busy} />
            <Button title="Kodu yeniden gönder" kind="secondary" onPress={sendCode} disabled={busy} />
          </>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
