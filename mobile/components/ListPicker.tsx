import { useEffect, useState } from 'react';
import { ActivityIndicator, Modal, Pressable, Text, View } from 'react-native';

import { Button, Input, Muted, useTheme } from '@/components/ui';
import { api, ListSummary } from '@/lib/api';

/** "Listeye ekle": alttan açılan pencerede liste seçilir ya da yeni liste oluşturulur */
export default function ListPicker({ visible, onClose, onPick }: {
  visible: boolean; onClose: () => void; onPick: (listId: number) => Promise<void>;
}) {
  const t = useTheme();
  const [lists, setLists] = useState<ListSummary[] | null>(null);
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!visible) return;
    api.lists().then(setLists).catch(e => setError(e.message));
  }, [visible]);

  const pick = async (id: number) => {
    setBusy(true);
    setError(null);
    try { await onPick(id); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  const createAndPick = async () => {
    if (!name.trim()) return;
    setBusy(true);
    try {
      const created = await api.createList(name.trim());
      setName('');
      await onPick(created.id);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' }} onPress={onClose} />
      <View style={{ backgroundColor: t.background, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, gap: 10, maxHeight: '75%' }}>
        <Text style={{ color: t.text, fontSize: 18, fontWeight: '800' }}>Hangi listeye?</Text>
        {lists === null && !error && <ActivityIndicator color={t.tint} />}
        {lists?.map(l => (
          <Pressable key={l.id} onPress={() => pick(l.id)} disabled={busy}
            style={{ padding: 14, borderRadius: 12, backgroundColor: t.card, borderWidth: 1, borderColor: t.border }}>
            <Text style={{ color: t.text, fontWeight: '600' }}>{l.name}</Text>
            <Muted>{l.item_count} ürün</Muted>
          </Pressable>
        ))}
        <View style={{ flexDirection: 'row', gap: 8 }}>
          <View style={{ flex: 1 }}><Input placeholder="Yeni liste adı" value={name} onChangeText={setName} /></View>
          <Button title="Oluştur" onPress={createAndPick} busy={busy} disabled={!name.trim()} />
        </View>
        {error && <Text style={{ color: t.danger }}>{error}</Text>}
      </View>
    </Modal>
  );
}
