import { useState } from 'react';
import { Text, View } from 'react-native';

import { Button, Card, Input, Muted, useTheme } from '@/components/ui';
import { api, GroupProduct } from '@/lib/api';
import { parseReportedPrice } from '@/lib/trust';

/**
 * "Bu fiyat yanlış": kasada ya da rafta farklı fiyat görüldüyse bildirilir. Gösterilen fiyatı sunucu kendi
 * verisinden bilir; kullanıcı yalnız gördüğü fiyatı (isteğe bağlı) ve notu yazar.
 */
export default function PriceReport({ groupId, product, storeId, shown, onClose }: {
  groupId: number; product: GroupProduct; storeId: number | null; shown: number; onClose: () => void;
}) {
  const t = useTheme();
  const [price, setPrice] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const send = async () => {
    if (price.trim() && parseReportedPrice(price) == null) { setMsg({ ok: false, text: 'Fiyatı sayı olarak yaz (örn. 45,50).' }); return; }
    setBusy(true);
    try {
      const r = await api.reportPrice(groupId, {
        product_id: product.id, store_id: storeId, reported_price: parseReportedPrice(price), note: note.trim() || null,
      });
      setMsg({ ok: true, text: r.detail });
    } catch (e) { setMsg({ ok: false, text: (e as Error).message }); } finally { setBusy(false); }
  };

  return (
    <Card style={{ gap: 8, margin: 12, borderColor: t.tint }}>
      <Text style={{ color: t.text, fontWeight: '700' }}>Bu fiyat yanlış mı?</Text>
      <Muted>{product.brand || product.name}: uygulamada {shown.toFixed(2)} ₺ görünüyor. Gördüğün fiyatı yaz (isteğe bağlı).</Muted>
      {msg?.ok ? <Text style={{ color: t.tint, fontWeight: '600' }}>{msg.text}</Text> : (
        <>
          <Input placeholder="Gördüğüm fiyat (₺)" value={price} onChangeText={setPrice} keyboardType="decimal-pad" />
          <Input placeholder="Not (örn. kasada 45,50 ödedim)" value={note} onChangeText={setNote} maxLength={300} />
          {msg && <Text style={{ color: t.danger }}>{msg.text}</Text>}
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <View style={{ flex: 1 }}><Button title="Bildir" onPress={send} busy={busy} /></View>
            <View style={{ flex: 1 }}><Button title="Vazgeç" kind="secondary" onPress={onClose} /></View>
          </View>
        </>
      )}
      {msg?.ok && <Button title="Kapat" kind="secondary" onPress={onClose} />}
    </Card>
  );
}
