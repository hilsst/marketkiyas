import { useEffect, useState } from 'react';
import { ActivityIndicator, Image, Text, View } from 'react-native';

import { Card, Input, Muted, Screen, Title, useTheme } from '@/components/ui';
import { api, formatSize, GroupSummary, num } from '@/lib/api';

/**
 * Ana sayfa. 1. adımda arama ve sonuç listesi (sunucu bağlantısının kanıtı); tasarruf kutusu, hızlı erişim,
 * kategoriler, fırsatlar ve yakındaki marketler 3. adımda web arayüzündeki sırayla gelir.
 */
export default function HomeScreen() {
  const t = useTheme();
  const [q, setQ] = useState('');
  const [results, setResults] = useState<GroupSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(() => {
      api.searchProducts(q.trim(), null, q.trim() ? {} : { sort: 'popular', limit: 20 })
        .then(r => { if (!cancelled) { setResults(r); setError(null); } })
        .catch(e => { if (!cancelled) setError(e.message); });
    }, q ? 300 : 0);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [q]);

  return (
    <Screen>
      <Title>🛒 Ucuzu</Title>
      <Input placeholder="🔍  Ürün ara (örn. süt, ekmek, deterjan)" value={q} onChangeText={setQ}
        returnKeyType="search" autoCorrect={false} />
      {error && <Text style={{ color: t.danger }}>{error}</Text>}
      {results === null && !error && <ActivityIndicator color={t.tint} style={{ marginTop: 24 }} />}
      {results?.length === 0 && <Muted style={{ textAlign: 'center', marginTop: 24 }}>Sonuç bulunamadı</Muted>}
      {results?.map(g => {
        const cheapest = [...g.market_prices].sort((a, b) => num(a.min_price) - num(b.min_price))[0];
        return (
          <Card key={g.id} style={{ flexDirection: 'row', gap: 12, alignItems: 'center' }}>
            {g.image_url
              ? <Image source={{ uri: g.image_url }} style={{ width: 52, height: 52, borderRadius: 8, backgroundColor: '#fff' }} resizeMode="contain" />
              : <Text style={{ fontSize: 36 }}>🛒</Text>}
            <View style={{ flex: 1, gap: 2 }}>
              <Text style={{ color: t.text, fontWeight: '600', fontSize: 15 }}>{g.name}</Text>
              <Muted>{[formatSize(g.quantity, g.unit), g.market_prices.length + ' market'].filter(Boolean).join(' · ')}</Muted>
              {cheapest && <Text style={{ color: t.tint, fontWeight: '700' }}>{num(cheapest.min_price).toFixed(2)} ₺</Text>}
            </View>
          </Card>
        );
      })}
    </Screen>
  );
}
