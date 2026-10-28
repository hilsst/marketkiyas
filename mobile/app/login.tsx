import { router } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from 'react-native';

import { Button, Input, Muted, useTheme } from '@/components/ui';
import { useAuth } from '@/lib/auth';

/** Giriş ve üyelik tek ekranda; Google/Apple ile giriş ve şifre sıfırlama 2. adımda gelir */
export default function LoginScreen() {
  const t = useTheme();
  const { login, register } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setError(null);
    if (!email.trim() || password.length < 8) {
      setError('E-posta ve en az 8 karakterli şifre girin.');
      return;
    }
    setBusy(true);
    try {
      if (mode === 'login') await login(email, password);
      else await register(email, password, fullName);
      router.back();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1, backgroundColor: t.background }}>
      <ScrollView contentContainerStyle={{ padding: 20, gap: 14 }} keyboardShouldPersistTaps="handled">
        <Text style={{ fontSize: 28, fontWeight: '800', color: t.text }}>🛒 MarketKıyas</Text>
        <Muted>{mode === 'login' ? 'Listelerin, tasarrufun ve marketlerin için giriş yap.' : 'Ücretsiz üye ol, alışverişte tasarrufunu takip et.'}</Muted>

        <View style={{ flexDirection: 'row', gap: 8 }}>
          {(['login', 'register'] as const).map(m => (
            <Pressable key={m} onPress={() => { setMode(m); setError(null); }}
              style={{ flex: 1, paddingVertical: 10, borderRadius: 12, alignItems: 'center',
                backgroundColor: mode === m ? t.tint : t.card, borderWidth: 1, borderColor: mode === m ? t.tint : t.border }}>
              <Text style={{ color: mode === m ? '#fff' : t.text, fontWeight: '600' }}>{m === 'login' ? 'Giriş yap' : 'Üye ol'}</Text>
            </Pressable>
          ))}
        </View>

        {mode === 'register' && (
          <Input placeholder="Ad soyad (isteğe bağlı)" value={fullName} onChangeText={setFullName} autoComplete="name" />
        )}
        <Input placeholder="E-posta" value={email} onChangeText={setEmail} autoCapitalize="none"
          keyboardType="email-address" autoComplete="email" textContentType="emailAddress" />
        <Input placeholder="Şifre (en az 8 karakter)" value={password} onChangeText={setPassword} secureTextEntry
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'} onSubmitEditing={submit} />

        {error && <Text style={{ color: t.danger }}>{error}</Text>}
        <Button title={mode === 'login' ? 'Giriş yap' : 'Üye ol'} onPress={submit} busy={busy} />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
