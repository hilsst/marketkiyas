import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Alert, Linking, Pressable, ScrollView, View } from 'react-native';
import { Text } from '@/components/Text';
import { SafeAreaView } from 'react-native-safe-area-context';

import AuthImage from '@/components/AuthImage';
import { Button, Card, Input, Muted, useTheme } from '@/components/ui';
import { API_URL, api, InstagramStatus, RecipePhotoInfo } from '@/lib/api';
import { useAuth } from '@/lib/auth';

type Tab = 'pending' | 'approved' | 'rejected';
const TABS: { key: Tab; label: string }[] = [
  { key: 'pending', label: 'Bekleyen' }, { key: 'approved', label: 'Onaylı' }, { key: 'rejected', label: 'Reddedilen' },
];

/** Yönetici: üye fotoğraflarını onayla/reddet; onaylı ve yükleyenin izin verdiği fotoğrafı Instagram'da yayınla. */
export default function AdminPhotos() {
  const t = useTheme();
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>('pending');
  const [items, setItems] = useState<RecipePhotoInfo[] | null>(null);
  const [ig, setIg] = useState<InstagramStatus | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<{ id: number; caption: string } | null>(null);

  const load = useCallback(() => {
    setItems(null); setError(null);
    api.adminRecipePhotos(tab).then(setItems).catch(e => setError(e instanceof Error ? e.message : 'Yüklenemedi'));
  }, [tab]);
  useEffect(load, [load]);
  useEffect(() => { api.instagramStatus().then(setIg).catch(() => setIg(null)); }, []);

  const replace = (p: RecipePhotoInfo) => setItems(list => (list ?? []).map(x => (x.id === p.id ? p : x)));

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

  const openPublish = async (p: RecipePhotoInfo) => {
    setBusy(p.id);
    try {
      const { caption } = await api.instagramCaption(p.id);
      setEditing({ id: p.id, caption });
    } catch (e) {
      Alert.alert('Altyazı alınamadı', e instanceof Error ? e.message : 'Tekrar deneyin');
    } finally {
      setBusy(null);
    }
  };

  const resolve = async (p: RecipePhotoInfo, published: boolean) => {
    setBusy(p.id);
    try { replace(await api.resolveInstagram(p.id, published)); }
    catch (e) { Alert.alert('İşlem başarısız', e instanceof Error ? e.message : 'Tekrar deneyin'); }
    finally { setBusy(null); }
  };

  const publish = async () => {
    if (!editing) return;
    const { id, caption } = editing;
    setBusy(id);
    try {
      const p = await api.publishToInstagram(id, caption);
      replace(p);
      setEditing(null);
      if (p.ig_status === 'failed') Alert.alert('Instagram yayını başarısız', p.ig_error ?? 'Tekrar deneyin');
    } catch (e) {
      Alert.alert('Yayınlanamadı', e instanceof Error ? e.message : 'Tekrar deneyin');
    } finally {
      setBusy(null);
    }
  };

  if (!user?.is_admin) return <SafeAreaView style={{ flex: 1, backgroundColor: t.background, padding: 16 }}><Muted>Bu sayfa yöneticilere özel.</Muted></SafeAreaView>;

  const banner = !ig ? null : ig.configured && ig.username
    ? { ok: true, text: `Instagram bağlı: @${ig.username}` }
    : { ok: false, text: !ig.enabled ? 'Instagram bağlantısı kapalı (INSTAGRAM_ENABLED ve anahtarlar sunucuda ayarlanmalı).'
        : ig.error ? `Instagram bağlantı hatası: ${ig.error}` : 'Instagram anahtarları eksik (INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID, PUBLIC_BASE_URL).' };

  const igBlock = (p: RecipePhotoInfo) => {
    if (p.status !== 'approved') {
      return p.ig_needs_removal ? <Text style={{ color: t.danger }}>Instagram'da yayında; profilden elle kaldırın.</Text> : null;
    }
    if (p.ig_status === 'published') {
      return (
        <View style={{ gap: 6 }}>
          <Text style={{ color: t.tint, fontWeight: '700' }}>Instagram'da yayınlandı</Text>
          {p.ig_permalink && <Button title="Gönderiyi aç" kind="secondary" onPress={() => Linking.openURL(p.ig_permalink!)} />}
        </View>
      );
    }
    if (!p.ig_consent) return <Muted>Yükleyen Instagram'da paylaşılmasına izin vermedi.</Muted>;
    return (
      <View style={{ gap: 8 }}>
        {p.ig_status === 'failed' && <Text style={{ color: t.danger }}>Son deneme başarısız: {p.ig_error}</Text>}
        {p.ig_status === 'failed' && p.ig_error?.includes('elle işaretle') && (
          <>
            <Button title="Instagram'da yayında: işaretle" kind="secondary" onPress={() => resolve(p, true)} busy={busy === p.id} />
            <Button title="Yayında değil: sıfırla" kind="secondary" onPress={() => resolve(p, false)} disabled={busy === p.id} />
          </>
        )}
        {p.ig_status === 'publishing' && <Muted>Yayın sürüyor; birazdan yenileyin.</Muted>}
        {editing?.id === p.id ? (
          <>
            <Input multiline value={editing.caption} onChangeText={c => setEditing({ id: p.id, caption: c })}
              style={{ minHeight: 140, textAlignVertical: 'top' }} accessibilityLabel="Instagram altyazısı" />
            <Muted>{editing.caption.length} / 2200 karakter</Muted>
            <Button title="Şimdi yayınla" onPress={publish} busy={busy === p.id} />
            <Button title="Vazgeç" kind="secondary" onPress={() => setEditing(null)} disabled={busy === p.id} />
          </>
        ) : (
          <Button title={p.ig_status === 'failed' ? 'Instagram\'da tekrar dene' : 'Instagram\'da yayınla'} onPress={() => openPublish(p)}
            busy={busy === p.id} disabled={!ig?.configured} />
        )}
      </View>
    );
  };

  return (
    <SafeAreaView edges={['bottom']} style={{ flex: 1, backgroundColor: t.background }}>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>
        {banner && <Text style={{ color: banner.ok ? t.tint : t.textMuted, fontWeight: '600' }}>{banner.text}</Text>}
        <View style={{ flexDirection: 'row', gap: 8 }}>
          {TABS.map(x => (
            <Pressable key={x.key} onPress={() => setTab(x.key)} accessibilityRole="tab" accessibilityState={{ selected: tab === x.key }}
              style={{ flex: 1, paddingVertical: 10, borderRadius: 999, borderWidth: 1, alignItems: 'center',
                borderColor: tab === x.key ? t.tint : t.border, backgroundColor: tab === x.key ? t.tintSoft : 'transparent' }}>
              <Text style={{ color: tab === x.key ? t.tint : t.text, fontWeight: '700' }}>{x.label}</Text>
            </Pressable>
          ))}
        </View>
        {error && <Text style={{ color: t.danger }}>{error}</Text>}
        {!items && !error && <ActivityIndicator color={t.tint} />}
        {items && items.length === 0 && <Muted>Bu listede fotoğraf yok.</Muted>}
        {items?.map(p => (
          <Card key={p.id} style={{ gap: 10 }}>
            <Text style={{ color: t.text, fontWeight: '800' }}>{p.recipe_name}</Text>
            <Muted>{p.credit}</Muted>
            <View style={{ alignItems: 'center' }}>
              <AuthImage url={`${API_URL}/recipe-photos/${p.id}/image`} width={240} height={300} />
            </View>
            {tab === 'pending' && (
              <>
                <Muted>{p.ig_consent ? 'Instagram paylaşımına izin verdi.' : 'Instagram paylaşımına izin vermedi.'}</Muted>
                <Button title="Onayla" onPress={() => review(p, true)} busy={busy === p.id} />
                <Button title="Reddet" kind="secondary" onPress={() => review(p, false)} disabled={busy === p.id} />
              </>
            )}
            {igBlock(p)}
          </Card>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}
