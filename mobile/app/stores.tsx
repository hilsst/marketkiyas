import { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Linking, Platform, Pressable, View } from 'react-native';
import { Text } from '@/components/Text';

import MarketBadge from '@/components/MarketBadge';
import { ActionBar, Button, Card, Chip, Input, LoginPrompt, Muted, Screen, SectionHeader, useTheme } from '@/components/ui';
import { api, Store } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { searchCities } from '@/lib/cities';
import { formatKm, getCoords, getManualCity, setManualCity } from '@/lib/location';

type Status = 'idle' | 'loading' | 'ready' | 'denied' | 'unavailable' | 'outside' | 'error';

// Marketlerim: konumdan (GPS) ya da elle seçilen ilden yakındaki şubeleri bulur, seçimi kaydeder
export default function StoresScreen() {
  const t = useTheme();
  const { user } = useAuth();
  const [status, setStatus] = useState<Status>('idle');
  const [city, setCity] = useState<string | null>(null);
  const [stores, setStores] = useState<Store[]>([]);
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const [query, setQuery] = useState('');
  const [showCities, setShowCities] = useState(false);
  const [saving, setSaving] = useState(false);

  const find = useCallback(async () => {
    setStatus('loading');
    const r = await getCoords();
    if (!r.coords) { setStatus(r.reason); setShowCities(true); return; }
    try {
      const list = await api.nearbyStores(r.coords);
      setStores(list);
      setStatus('ready');
    } catch { setStatus('error'); }
  }, []);

  useEffect(() => {
    if (!user) return;
    api.myStores().then(mine => setPicked(new Set(mine.map(s => s.id)))).catch(() => {});
    void getManualCity().then(c => setCity(c?.name ?? null)).then(find);
  }, [user, find]);

  const chooseCity = async (name: string | null) => {
    await setManualCity(name);
    setCity(name);
    setShowCities(false);
    setQuery('');
    await find();
  };

  const toggle = (id: number) => setPicked(prev => { const n = new Set(prev); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const save = async () => {
    setSaving(true);
    try {
      await api.selectStores([...picked]);
      Alert.alert('Kaydedildi', 'Fiyatlar seçtiğiniz şubelere göre hesaplanacak.');
    } catch { Alert.alert('Kaydedilemedi', 'Biraz sonra tekrar deneyin.'); }
    setSaving(false);
  };

  const cities = useMemo(() => searchCities(query), [query]);
  if (!user) return <Screen safeTop={false}><LoginPrompt what="Marketlerinizi seçmek" /></Screen>;

  const problem: Partial<Record<Status, string>> = {
    denied: 'Konum izni kapalı. İzin verebilir ya da aşağıdan ilinizi seçebilirsiniz.',
    unavailable: 'Konumunuz alınamadı. Tekrar deneyebilir ya da ilinizi seçebilirsiniz.',
    outside: 'Konumunuz Türkiye dışında görünüyor. İlinizi seçerek devam edebilirsiniz.',
    error: 'Yakındaki marketler getirilemedi. Biraz sonra tekrar deneyin.',
  };

  return (
    <Screen safeTop={false} footer={status === 'ready' ? (
      <ActionBar><Button title={`Seçimi kaydet (${picked.size})`} onPress={save} busy={saving} /></ActionBar>
    ) : undefined}>
      <Card style={{ gap: 10 }}>
        <Text style={{ color: t.text, fontWeight: '700', fontSize: 16 }}>
          {city ? `Konum: ${city} (elle seçildi)` : 'Konum: telefonunuzun konumu'}
        </Text>
        <Muted>Konumunuz yalnızca yakındaki şubeleri bulmak için kullanılır, kaydedilmez.</Muted>
        {problem[status] ? <Text style={{ color: t.text }}>{problem[status]}</Text> : null}
        <Button title="Konumumu kullan" kind={city ? 'secondary' : 'primary'} busy={status === 'loading'}
          onPress={async () => {
            if (status === 'denied' && Platform.OS !== 'web') { await Linking.openSettings(); return; }
            await chooseCity(null);
          }} />
        <Button title={showCities ? 'İl listesini gizle' : 'İlimi kendim seçeceğim'} kind="secondary" onPress={() => setShowCities(s => !s)} />
        {showCities && (
          <View style={{ gap: 8 }}>
            <Input placeholder="İl ara (örn. Ankara)" value={query} onChangeText={setQuery} autoCorrect={false} accessibilityLabel="İl ara" />
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
              {cities.slice(0, 24).map(c => <Chip key={c.name} label={c.name} on={c.name === city} onPress={() => chooseCity(c.name)} />)}
            </View>
            {cities.length === 0 && <Muted>Bu adla il bulunamadı.</Muted>}
          </View>
        )}
      </Card>

      {status === 'ready' && (
        <View style={{ gap: 10 }}>
          <SectionHeader title="Yakınınızdaki şubeler" />
          {stores.length === 0 && <Card><Muted>Bu çevrede market şubesi bulunamadı. Başka bir il seçmeyi deneyin.</Muted></Card>}
          {stores.length > 0 && (
            <Card style={{ padding: 0 }}>
              {stores.map((s, i) => (
                <Pressable key={s.id} onPress={() => toggle(s.id)} accessibilityRole="checkbox"
                  accessibilityLabel={`${s.market_name} ${s.name}`} accessibilityState={{ checked: picked.has(s.id) }}
                  style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, minHeight: 56, borderTopWidth: i ? 1 : 0, borderTopColor: t.border }}>
                  <MarketBadge id={s.market_id} size={30} />
                  <View style={{ flex: 1 }}>
                    <Text style={{ color: t.text, fontWeight: '600' }} numberOfLines={1}>{s.name}</Text>
                    <Muted>{s.market_name}{s.distance_km != null ? ` · ${formatKm(s.distance_km)}` : ''}</Muted>
                  </View>
                  <Text style={{ color: picked.has(s.id) ? t.tint : t.textMuted, fontSize: 22 }}>{picked.has(s.id) ? '☑' : '☐'}</Text>
                </Pressable>
              ))}
            </Card>
          )}
        </View>
      )}
    </Screen>
  );
}
