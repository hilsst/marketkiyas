import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Alert, ScrollView, View } from 'react-native';
import { Text } from '@/components/Text';
import { SafeAreaView } from 'react-native-safe-area-context';

import AuthImage from '@/components/AuthImage';
import { Button, Card, Muted, useTheme } from '@/components/ui';
import { API_URL, api, RecipePhotoInfo } from '@/lib/api';
import { useAuth } from '@/lib/auth';

/** Yönetici: onay bekleyen üye fotoğrafları. Onaylanan tarifte herkese görünür. */
export default function AdminPhotos() {
  const t = useTheme();
  const { user } = useAuth();
  const [items, setItems] = useState<RecipePhotoInfo[] | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.adminRecipePhotos().then(setItems).catch(e => setError(e instanceof Error ? e.message : 'Yüklenemedi'));
  }, []);
  useEffect(load, [load]);

  const review = async (p: RecipePhotoInfo, approve: boolean) => {
    setBusy(p.id);
    try {
      await api.reviewRecipePhoto(p.id, approve);
      setItems(list => (list ?? []).filter(x => x.id !== p.id));
    } catch (e) {
      Alert.alert('İşlem başarısız', e instanceof Error ? e.message : 'Tekrar deneyin');
    } finally {
      setBusy(null);
    }
  };

  if (!user?.is_admin) return <SafeAreaView style={{ flex: 1, backgroundColor: t.background, padding: 16 }}><Muted>Bu sayfa yöneticilere özel.</Muted></SafeAreaView>;
  return (
    <SafeAreaView edges={['bottom']} style={{ flex: 1, backgroundColor: t.background }}>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>
        {error && <Text style={{ color: t.danger }}>{error}</Text>}
        {!items && !error && <ActivityIndicator color={t.tint} />}
        {items && items.length === 0 && <Muted>Onay bekleyen fotoğraf yok.</Muted>}
        {items?.map(p => (
          <Card key={p.id} style={{ gap: 10 }}>
            <Text style={{ color: t.text, fontWeight: '800' }}>{p.recipe_name}</Text>
            <Muted>{p.credit}</Muted>
            <View style={{ alignItems: 'center' }}>
              <AuthImage url={`${API_URL}/recipe-photos/${p.id}/image`} width={240} height={300} />
            </View>
            <Button title="Onayla" onPress={() => review(p, true)} busy={busy === p.id} />
            <Button title="Reddet" kind="secondary" onPress={() => review(p, false)} disabled={busy === p.id} />
          </Card>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}
