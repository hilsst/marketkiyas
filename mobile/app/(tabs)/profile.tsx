import { useEffect, useState } from 'react';
import { Text, View } from 'react-native';

import { Button, Card, Input, LoginPrompt, Muted, Screen, Title, useTheme } from '@/components/ui';
import { api, num, SavingsVault } from '@/lib/api';
import { useAuth } from '@/lib/auth';

export default function ProfileScreen() {
  const t = useTheme();
  const { user, logout, deleteAccount } = useAuth();
  const [vault, setVault] = useState<SavingsVault | null>(null);
  // Hesap silme: mağazaların zorunlu tuttuğu, geri alınamaz işlem; önce onay kutusu açılır
  const [deleting, setDeleting] = useState(false);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    api.savings().then(setVault).catch(() => setVault(null));
  }, [user]);

  const confirmDelete = async () => {
    setError(null);
    setBusy(true);
    try {
      await deleteAccount(user?.has_password ? password : undefined);
      setDeleting(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen>
      <Title>👤 Profil</Title>
      {!user ? <LoginPrompt what="Tasarrufunu ve marketlerini görmek" /> : (
        <>
          <Card style={{ gap: 4 }}>
            <Text style={{ color: t.text, fontSize: 17, fontWeight: '700' }}>{user.full_name || 'Ucuzu üyesi'}</Text>
            <Muted>{user.email}</Muted>
          </Card>
          <View style={{ backgroundColor: t.tint, borderRadius: 16, padding: 18, gap: 4 }}>
            <Text style={{ color: '#fff', fontSize: 12, fontWeight: '700', opacity: 0.9 }}>TOPLAM TASARRUF</Text>
            <Text style={{ color: '#fff', fontSize: 36, fontWeight: '900' }}>{num(vault?.total_saved).toFixed(2)} ₺</Text>
            <Text style={{ color: '#fff', fontSize: 12, opacity: 0.85 }}>{vault?.record_count ?? 0} alışveriş</Text>
          </View>
          <Button title="Çıkış yap" kind="secondary" onPress={logout} />

          {!deleting ? (
            <Text onPress={() => setDeleting(true)} style={{ color: t.danger, textAlign: 'center', padding: 8 }}>Hesabımı sil</Text>
          ) : (
            <Card style={{ gap: 10, borderColor: t.danger }}>
              <Text style={{ color: t.danger, fontWeight: '700' }}>Hesabın kalıcı olarak silinecek</Text>
              <Muted>Listelerin, tasarruf kasan, alarmların ve marketlerin silinir. Bu işlem geri alınamaz.</Muted>
              {user.has_password && (
                <Input placeholder="Onay için şifren" value={password} onChangeText={setPassword} secureTextEntry autoComplete="current-password" />
              )}
              {error && <Text style={{ color: t.danger }}>{error}</Text>}
              <Button title="Evet, hesabımı sil" onPress={confirmDelete} busy={busy} disabled={user.has_password && !password} />
              <Button title="Vazgeç" kind="secondary" onPress={() => { setDeleting(false); setPassword(''); setError(null); }} />
            </Card>
          )}
        </>
      )}
    </Screen>
  );
}
