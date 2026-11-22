import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Switch, View } from 'react-native';
import { Text } from '@/components/Text';

import FamilySection from '@/components/FamilySection';
import { Button, Card, Chip, Input, LoginPrompt, Muted, Screen, Title, useTheme } from '@/components/ui';
import { FONT_SIZES, useFontScale } from '@/lib/fontScale';
import { api, num, SavingsVault } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { accountRedirect } from '@/lib/guest';
import { disableWeekly, enableWeekly, isWeeklyOn, weeklySupported } from '@/lib/weekly';
import { formatTL } from '@/lib/format';
import { friendlyError } from '@/lib/errors';

export default function ProfileScreen() {
  const t = useTheme();
  const { user, logout, deleteAccount } = useAuth();
  const { size, setSize } = useFontScale();
  const [vault, setVault] = useState<SavingsVault | null>(null);
  // Hesap silme: mağazaların zorunlu tuttuğu, geri alınamaz işlem; önce onay kutusu açılır
  const [deleting, setDeleting] = useState(false);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [weekly, setWeekly] = useState(false);
  const [weeklyNote, setWeeklyNote] = useState<string | null>(null);
  useEffect(() => { void isWeeklyOn().then(setWeekly).catch(() => {}); }, []);

  const toggleWeekly = async (on: boolean) => {
    setWeeklyNote(null);
    try {
      if (on) {
        const ok = await enableWeekly(null);
        setWeekly(ok);
        if (!ok) setWeeklyNote('Bildirim izni verilmedi. Telefon ayarlarından Ucuzu için bildirimi açabilirsiniz.');
      } else { await disableWeekly(); setWeekly(false); }
    } catch (e) { setWeeklyNote(friendlyError(e)); }
  };

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
      setError(friendlyError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen>
      <Title>Hesabım</Title>
      <Card style={{ gap: 10 }}>
        <Text accessibilityRole="header" style={{ color: t.text, fontWeight: '700', fontSize: 17 }}>Yazı boyutu</Text>
        <Muted>Telefonunuzun yazı boyutu ayarına ek olarak çalışır.</Muted>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
          {FONT_SIZES.map(f => <Chip key={f.key} label={f.label} on={size === f.key} onPress={() => setSize(f.key)} />)}
        </View>
        <Text style={{ color: t.text, fontSize: 16 }}>Önizleme: Pınar Süt 1L · 31,95 ₺</Text>
      </Card>
      {!user ? <LoginPrompt what="Tasarrufunu ve marketlerini görmek" /> : (
        <>
          <Card style={{ gap: 4 }}>
            <Text style={{ color: t.text, fontSize: 17, fontWeight: '700' }}>{user.is_guest ? 'Misafir' : user.full_name || 'Ucuzu üyesi'}</Text>
            <Muted>{user.is_guest ? 'Hesapsız kullanıyorsunuz. Planlarınız ve listeleriniz bu telefonda duruyor.' : user.email}</Muted>
          </Card>
          {user.is_guest && (
            <Card style={{ gap: 8, borderColor: t.tint }}>
              <Text style={{ color: t.text, fontWeight: '700' }}>Ücretsiz hesap aç</Text>
              <Muted>Planlarınızı kaydedin, listenizi paylaşın, tasarrufunuzu her ay görün. Şu anki verileriniz olduğu gibi kalır.</Muted>
              <Button title="Hesap aç" onPress={() => { const to = accountRedirect(user, 'save'); if (to) router.push(to); }} />
            </Card>
          )}
          <View style={{ backgroundColor: t.tint, borderRadius: 16, padding: 18, gap: 4 }}>
            <Text style={{ color: t.onTint, fontSize: 14, fontWeight: '700' }}>TOPLAM TASARRUF</Text>
            <Text style={{ color: t.onTint, fontSize: 36, fontWeight: '900' }}>{formatTL(num(vault?.total_saved))} ₺</Text>
            <Text style={{ color: t.onTint, fontSize: 14 }}>{vault?.record_count ?? 0} alışveriş</Text>
          </View>
          {weeklySupported && (
            <Card style={{ gap: 6 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                <View style={{ flex: 1 }}>
                  <Text style={{ color: t.text, fontWeight: '700' }}>Haftalık menü bildirimi</Text>
                  <Muted>{'Her pazar 11:00\'de "Bu haftanın menüsü hazır" der; dokununca planı açar.'}</Muted>
                </View>
                <Switch value={weekly} onValueChange={toggleWeekly} />
              </View>
              {weeklyNote && <Text style={{ color: t.danger }}>{weeklyNote}</Text>}
            </Card>
          )}
          <Button title="Karşılama ekranını göster" kind="secondary" onPress={() => router.push('/welcome')} />
          {user.is_admin && <Button title="Fotoğraf onayı (yönetici)" kind="secondary" onPress={() => router.push('/admin/photos')} />}
          {!user.is_guest && <FamilySection user={user} />}
          {!user.is_guest && <Button title="Çıkış yap" kind="secondary" onPress={logout} />}

          {!deleting ? (
            <Text onPress={() => setDeleting(true)} style={{ color: t.danger, textAlign: 'center', padding: 8 }}>{user.is_guest ? 'Verilerimi sil' : 'Hesabımı sil'}</Text>
          ) : (
            <Card style={{ gap: 10, borderColor: t.danger }}>
              <Text style={{ color: t.danger, fontWeight: '700' }}>Hesabınız kalıcı olarak silinecek</Text>
              <Muted>Listeleriniz, tasarruf kasanız, takip ettiğiniz ürünler ve marketleriniz silinir. Bu işlem geri alınamaz.</Muted>
              {user.has_password && (
                <Input placeholder="Onay için şifreniz" value={password} onChangeText={setPassword} secureTextEntry autoComplete="current-password" />
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
