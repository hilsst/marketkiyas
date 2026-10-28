import { Card, LoginPrompt, Muted, Screen, Title } from '@/components/ui';
import { useAuth } from '@/lib/auth';

// Fiyat alarmları ve bildirimler 7. adımda
export default function AlertsScreen() {
  const { user } = useAuth();
  return (
    <Screen>
      <Title>🔔 Alarmlar</Title>
      {user ? <Card><Muted>Takip ettiğin ürünlerin fiyatı düşünce burada görünecek.</Muted></Card> : <LoginPrompt what="Fiyat alarmı kurmak" />}
    </Screen>
  );
}
