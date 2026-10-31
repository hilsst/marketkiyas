import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Card, Input, Muted, useTheme } from '@/components/ui';
import { api, formatSize, PantryItem } from '@/lib/api';

const dateLabel = (iso: string) => new Date(iso + 'T12:00:00').toLocaleDateString('tr-TR', { day: 'numeric', month: 'long' });

/**
 * Dolabım: alınan paketlerden artanlar (ör. 500 g'lık mercimekten artan 300 g). Plan alışveriş
 * listesine aktarılınca kendiliğinden yazılır; sonraki planlar önce bunları kullanır. Miktar elle
 * düzeltilebilir ya da malzeme çıkarılabilir.
 */
export default function PantryScreen() {
  const t = useTheme();
  const [items, setItems] = useState<PantryItem[] | null>(null);
  const [editing, setEditing] = useState<number | null>(null);
  const [value, setValue] = useState('');
  const [error, setError] = useState<string | null>(null);

  useFocusEffect(useCallback(() => {
    api.pantry().then(setItems).catch(e => setError((e as Error).message));
  }, []));

  const save = async (id: number) => {
    const qty = Number(value.replace(',', '.'));
    if (!(qty >= 0)) return;
    try { setItems(await api.updatePantry(id, qty)); setEditing(null); } catch (e) { setError((e as Error).message); }
  };
  const remove = async (id: number) => {
    try { setItems(await api.deletePantry(id)); } catch (e) { setError((e as Error).message); }
  };

  return (
    <SafeAreaView edges={[]} style={{ flex: 1, backgroundColor: t.background }}>
      <ScrollView keyboardShouldPersistTaps="handled">
        <View style={{ padding: 16, gap: 12 }}>
          <Muted>
            Planı alışveriş listesine aktardığında paketlerden artacak miktarlar buraya yazılır. Yeni planlar önce
            bunları kullanır, yalnız eksik kısım listeye eklenir. Bozulabilenler son günü geçince kendiliğinden çıkar.
          </Muted>
          {error && <Text style={{ color: t.danger }}>{error}</Text>}
          {items === null ? <ActivityIndicator color={t.tint} /> : items.length === 0 ? (
            <Card><Muted>Dolabın boş. Bir planı listeye aktardığında artanlar burada görünür.</Muted></Card>
          ) : items.map(item => (
            <Card key={item.id} style={{ gap: 8 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                <View style={{ flex: 1 }}>
                  <Text style={{ color: t.text, fontWeight: '700', fontSize: 16 }}>{item.name}</Text>
                  <Muted style={{ fontSize: 12 }}>{item.expires_on ? `Son gün: ${dateLabel(item.expires_on)}` : 'Bozulmaz'}</Muted>
                </View>
                <Text style={{ color: t.text, fontWeight: '800', fontSize: 16 }}>{formatSize(item.quantity, item.unit)}</Text>
              </View>
              {editing === item.id ? (
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <Input style={{ flex: 1 }} keyboardType="numeric" value={value} autoFocus
                    onChangeText={v => setValue(v.replace(/[^0-9.,]/g, ''))} onSubmitEditing={() => save(item.id)} />
                  <Muted>{item.unit === 'adet' ? 'adet' : item.unit}</Muted>
                  <Text style={{ color: t.tint, fontWeight: '700' }} onPress={() => save(item.id)}>Kaydet</Text>
                </View>
              ) : (
                <View style={{ flexDirection: 'row', gap: 18 }}>
                  <Pressable onPress={() => { setEditing(item.id); setValue(String(Number(item.quantity))); }}>
                    <Text style={{ color: t.tint, fontWeight: '600' }}>Miktarı düzelt</Text>
                  </Pressable>
                  <Pressable onPress={() => remove(item.id)}>
                    <Text style={{ color: t.danger, fontWeight: '600' }}>Bitti, çıkar</Text>
                  </Pressable>
                </View>
              )}
            </Card>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
