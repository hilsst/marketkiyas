import { useEffect, useState } from 'react';
import { Text, View } from 'react-native';

import { Button, Card, LoginPrompt, Muted, Screen, Title, useTheme } from '@/components/ui';
import { api, num, SavingsVault } from '@/lib/api';
import { useAuth } from '@/lib/auth';

export default function ProfileScreen() {
  const t = useTheme();
  const { user, logout } = useAuth();
  const [vault, setVault] = useState<SavingsVault | null>(null);

  useEffect(() => {
    if (!user) return;
    api.savings().then(setVault).catch(() => setVault(null));
  }, [user]);

  return (
    <Screen>
      <Title>👤 Profil</Title>
      {!user ? <LoginPrompt what="Tasarrufunu ve marketlerini görmek" /> : (
        <>
          <Card style={{ gap: 4 }}>
            <Text style={{ color: t.text, fontSize: 17, fontWeight: '700' }}>{user.full_name || 'MarketKıyas üyesi'}</Text>
            <Muted>{user.email}</Muted>
          </Card>
          <View style={{ backgroundColor: t.tint, borderRadius: 16, padding: 18, gap: 4 }}>
            <Text style={{ color: '#fff', fontSize: 12, fontWeight: '700', opacity: 0.9 }}>TOPLAM TASARRUF</Text>
            <Text style={{ color: '#fff', fontSize: 36, fontWeight: '900' }}>{num(vault?.total_saved).toFixed(2)} ₺</Text>
            <Text style={{ color: '#fff', fontSize: 12, opacity: 0.85 }}>{vault?.record_count ?? 0} alışveriş</Text>
          </View>
          <Button title="Çıkış yap" kind="secondary" onPress={logout} />
        </>
      )}
    </Screen>
  );
}
