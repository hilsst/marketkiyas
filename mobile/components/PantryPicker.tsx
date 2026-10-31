import { router } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Modal, Pressable, ScrollView, Text, View } from 'react-native';

import { Button, Input, Muted, useTheme } from '@/components/ui';
import { api, IngredientChoice, RecipeSummary } from '@/lib/api';

/** Türkçe harfleri sadeleştirip küçült: "Soğan" ~ "sogan" */
const normalize = (s: string) => s.toLocaleLowerCase('tr-TR')
  .replace(/ç/g, 'c').replace(/ğ/g, 'g').replace(/ı/g, 'i').replace(/ö/g, 'o').replace(/ş/g, 's').replace(/ü/g, 'u').trim();

/**
 * "Dolabımda ne var": evdeki malzemeleri seç. Seçilenler planın maliyetine ve alışveriş listesine
 * girmez, bunları kullanan tarifler öne çıkar. Altta bu malzemelerle yapılabilecek tarifler ve
 * eksikleri görünür.
 */
export default function PantryPicker({ initial, onClose }: { initial: string[]; onClose: (have: string[]) => void }) {
  const t = useTheme();
  const [choices, setChoices] = useState<IngredientChoice[] | null>(null);
  const [have, setHave] = useState<string[]>(initial);
  const [query, setQuery] = useState('');
  const [recipes, setRecipes] = useState<RecipeSummary[]>([]);

  useEffect(() => { api.ingredients().then(setChoices).catch(() => setChoices([])); }, []);
  useEffect(() => {
    if (!have.length) return;
    let live = true;
    api.pantryRecipes(have).then(r => { if (live) setRecipes(r); }).catch(() => {});
    return () => { live = false; };
  }, [have]);

  const shown = useMemo(() => {
    const q = normalize(query);
    const list = (choices ?? []).filter(c => !q || normalize(c.name).includes(q));
    return q ? list : list.slice(0, 40);
  }, [choices, query]);

  const toggle = (name: string) => setHave(cur => cur.includes(name) ? cur.filter(n => n !== name) : [...cur, name]);
  const chip = (name: string, active: boolean) => (
    <Pressable key={name} onPress={() => toggle(name)}
      style={{ paddingHorizontal: 12, paddingVertical: 7, borderRadius: 999, borderWidth: 1,
        borderColor: active ? t.tint : t.border, backgroundColor: active ? t.tint : t.card }}>
      <Text style={{ color: active ? '#fff' : t.text, fontWeight: '600', fontSize: 13 }}>{active ? '✓ ' : ''}{name}</Text>
    </Pressable>
  );

  return (
    <Modal visible animationType="slide" onRequestClose={() => onClose(have)}>
      <View style={{ flex: 1, backgroundColor: t.background }}>
        <View style={{ backgroundColor: t.tint, paddingTop: 48, paddingBottom: 16, paddingHorizontal: 20, gap: 4 }}>
          <Text style={{ color: '#fff', fontSize: 22, fontWeight: '800' }}>🧺 Dolabımda ne var?</Text>
          <Text style={{ color: '#fff', opacity: 0.9 }}>
            Evde olanları seç. Dolabım’a da eklenir; bunları kullanan yemekler öne çıkar, alışveriş listesine eklenmez.
          </Text>
        </View>
        <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }} keyboardShouldPersistTaps="handled">
          <Input placeholder="Malzeme ara (nohut, pirinç, yoğurt...)" value={query} onChangeText={setQuery} />
          {have.length > 0 && (
            <View style={{ gap: 6 }}>
              <Muted>Seçtiklerin ({have.length})</Muted>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>{have.map(n => chip(n, true))}</View>
            </View>
          )}
          {have.length > 0 && recipes.length > 0 && (
            <View style={{ gap: 8 }}>
              <Text style={{ color: t.text, fontWeight: '800', fontSize: 17 }}>Bunlarla yapılabilecekler</Text>
              {recipes.slice(0, 8).map(r => (
                <Pressable key={r.id} onPress={() => router.push({ pathname: '/recipe/[id]', params: { id: String(r.id) } })}
                  style={{ flexDirection: 'row', gap: 10, alignItems: 'center', padding: 10, borderRadius: 14, borderWidth: 1, borderColor: t.border, backgroundColor: t.card }}>
                  <Text style={{ fontSize: 28 }}>{r.icon ?? '🍽️'}</Text>
                  <View style={{ flex: 1 }}>
                    <Text style={{ color: t.text, fontWeight: '700' }}>{r.name}</Text>
                    <Muted style={{ fontSize: 12 }}>
                      {r.missing && r.missing.length ? `Eksik: ${r.missing.join(', ')}` : '✓ Hepsi evde var'}
                    </Muted>
                  </View>
                </Pressable>
              ))}
            </View>
          )}
          {choices === null ? <ActivityIndicator color={t.tint} /> : (
            <View style={{ gap: 6 }}>
              <Muted>{query ? 'Arama sonuçları' : 'En çok kullanılan malzemeler'}</Muted>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
                {shown.filter(c => !have.includes(c.name)).map(c => chip(c.name, false))}
              </View>
              {shown.length === 0 && <Muted>Tariflerde bu malzeme yok.</Muted>}
            </View>
          )}

        </ScrollView>
        <View style={{ padding: 16, gap: 8, borderTopWidth: 1, borderTopColor: t.border }}>
          <Button title={have.length ? `Tamam (${have.length} malzeme)` : 'Tamam'} onPress={() => onClose(have)} />
          {have.length > 0 && <Text style={{ color: t.danger, textAlign: 'center' }} onPress={() => setHave([])}>Hepsini temizle</Text>}
        </View>
      </View>
    </Modal>
  );
}
