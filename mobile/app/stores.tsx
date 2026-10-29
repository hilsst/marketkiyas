import { Card, Muted, Screen } from '@/components/ui';

// Marketlerim (konum izni, yakındaki şubeler, seçim) 6. adımda
export default function StoresScreen() {
  return (
    <Screen safeTop={false}>
      <Card><Muted>Yakınındaki şubeleri seçeceğin ekran 6. adımda geliyor.</Muted></Card>
    </Screen>
  );
}
