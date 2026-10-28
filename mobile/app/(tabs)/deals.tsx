import { Card, Muted, Screen, Title } from '@/components/ui';

// Fırsatlar listesi 3. adımda (sunucu: GET /products/deals)
export default function DealsScreen() {
  return (
    <Screen>
      <Title>🏷️ Fırsatlar</Title>
      <Card><Muted>Seçtiğin marketlerdeki indirimli ürünler burada olacak.</Muted></Card>
    </Screen>
  );
}
