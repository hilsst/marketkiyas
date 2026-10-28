import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';

import MarketBadge from '@/components/MarketBadge';
import { Button, Card, Input, LoginPrompt, Muted, Screen, Title, useTheme } from '@/components/ui';
import { api, ListSummary, num } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { useCatalog } from '@/lib/catalog';

export default function ListsScreen() {
  const t = useTheme();
  const { user } = useAuth();
  const { marketById } = useCatalog();
  const [lists, setLists] = useState<ListSummary[] | null>(null);
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Liste ekranından dönünce toplamlar tazelensin
  useFocusEffect(useCallback(() => {
    if (!user) return;
    api.lists().then(setLists).catch(e => setError(e.message));
  }, [user]));

  const create = async () => {
    if (!name.trim()) return;
    setBusy(true);
    try {
      const created = await api.createList(name.trim());
      setName('');
      router.push({ pathname: '/list/[id]', params: { id: String(created.id) } });
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <Screen>
      <Title>📋 Listeler</Title>
      {!user ? <LoginPrompt what="Alışveriş listesi oluşturmak" /> : (
        <>
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <View style={{ flex: 1 }}>
              <Input placeholder="Yeni liste adı (örn. Haftalık)" value={name} onChangeText={setName} onSubmitEditing={create} returnKeyType="done" />
            </View>
            <Button title="Ekle" onPress={create} busy={busy} disabled={!name.trim()} />
          </View>
          {error && <Text style={{ color: t.danger }}>{error}</Text>}
          {lists === null && !error && <ActivityIndicator color={t.tint} />}
          {lists?.length === 0 && <Muted style={{ textAlign: 'center' }}>Henüz listen yok. Yukarıdan ilk listeni oluştur.</Muted>}
          {lists?.map(l => (
            <Pressable key={l.id} onPress={() => router.push({ pathname: '/list/[id]', params: { id: String(l.id) } })}>
              <Card style={{ gap: 6 }}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text style={{ color: t.text, fontWeight: '700', fontSize: 16, flex: 1 }} numberOfLines={1}>{l.name}</Text>
                  <Muted>{l.item_count} ürün</Muted>
                </View>
                {l.status === 'shopping' && <Text style={{ color: t.tint, fontWeight: '700', fontSize: 12 }}>🛒 Alışveriş sürüyor · {l.checked_count}/{l.item_count} alındı</Text>}
                {l.estimated_total != null && (
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                    <Muted>Tahmini: </Muted>
                    <Text style={{ color: t.text, fontWeight: '800' }}>{num(l.estimated_total).toFixed(2)} ₺</Text>
                    {l.top_market_id != null && <><MarketBadge id={l.top_market_id} size={18} /><Muted>en çok {marketById(l.top_market_id)?.name}</Muted></>}
                  </View>
                )}
              </Card>
            </Pressable>
          ))}
        </>
      )}
    </Screen>
  );
}
