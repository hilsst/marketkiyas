import { router, useLocalSearchParams } from 'expo-router';
import { Fragment, useEffect, useState } from 'react';
import { ActivityIndicator, Text } from 'react-native';

import AdSlot from '@/components/AdSlot';
import ProductRow from '@/components/ProductRow';
import { Input, Muted, Screen, useTheme } from '@/components/ui';
import { api, GroupSummary } from '@/lib/api';

/** Ürün araması. Ana sayfadaki arama çubuğu buraya açılır. */
export default function SearchScreen() {
  const t = useTheme();
  // listId: liste ekranındaki 'Ürün ekle'den gelindiyse ürün doğrudan o listeye eklenir
  const params = useLocalSearchParams<{ q?: string; listId?: string }>();
  const [q, setQ] = useState(params.q ?? '');
  const [results, setResults] = useState<GroupSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const term = q.trim();
    let cancelled = false;
    const timer = setTimeout(() => {
      if (!term) { setResults([]); return; }
      api.searchProducts(term)
        .then(r => { if (!cancelled) { setResults(r); setError(null); } })
        .catch(e => { if (!cancelled) setError(e.message); });
    }, 300);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [q]);

  return (
    <Screen safeTop={false}>
      <Input placeholder="🔍  Ürün ara (örn. süt, ekmek, deterjan)" value={q} onChangeText={setQ}
        autoFocus returnKeyType="search" autoCorrect={false} />
      {error && <Text style={{ color: t.danger }}>{error}</Text>}
      {results === null && !error && <ActivityIndicator color={t.tint} style={{ marginTop: 24 }} />}
      {q.trim() !== '' && results?.length === 0 && <Muted style={{ textAlign: 'center', marginTop: 24 }}>Sonuç bulunamadı</Muted>}
      {results?.map((g, i) => (
        <Fragment key={g.id}>
          <ProductRow group={g} onPress={() => router.push({ pathname: '/product/[id]', params: params.listId ? { id: String(g.id), listId: params.listId } : { id: String(g.id) } })} />
          {i % 4 === 3 && <AdSlot placement="list" />}
        </Fragment>
      ))}
    </Screen>
  );
}
