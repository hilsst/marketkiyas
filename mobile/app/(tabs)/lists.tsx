import { Card, LoginPrompt, Muted, Screen, Title } from '@/components/ui';
import { useAuth } from '@/lib/auth';

// Listeler, planlar ve alışveriş modu 5. adımda
export default function ListsScreen() {
  const { user } = useAuth();
  return (
    <Screen>
      <Title>📋 Listeler</Title>
      {user ? <Card><Muted>Alışveriş listelerin burada olacak.</Muted></Card> : <LoginPrompt what="Alışveriş listesi oluşturmak" />}
    </Screen>
  );
}
