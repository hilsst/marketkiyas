import { useState } from 'react';
import { Modal, Pressable, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Button, Input, Muted, useTheme } from '@/components/ui';
import { api, num, PriceAlert } from '@/lib/api';

/**
 * "Fiyatını takip et": fiyat düşünce ya da yazılan fiyatın altına inince Alarmlar sekmesinde haber verilir.
 * Ürün sayfasında bir satır seçiliyse (marka/market) yalnızca o ürün takip edilir, değilse en ucuzu.
 */
export default function AlertSheet({ visible, onClose, groupId, groupName, cheapest, product, alert, onChange }: {
  visible: boolean; onClose: () => void; groupId: number; groupName: string; cheapest: number | null;
  product: { id: number; label: string; price: number } | null;
  alert: PriceAlert | null; onChange: (alert: PriceAlert | null, message: string) => void;
}) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const [target, setTarget] = useState(alert?.target_price ? num(alert.target_price).toFixed(2) : '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async (withTarget: boolean) => {
    const value = Number(target.replace(',', '.'));
    if (withTarget && !(value > 0)) { setError('Geçerli bir fiyat yaz (örn. 30,00)'); return; }
    setBusy(true);
    setError(null);
    try {
      const all = await api.createAlert(groupId, withTarget ? value : null, product?.id ?? null);
      onChange(all.find(a => a.group_id === groupId) || null,
        withTarget ? `Fiyat ${value.toFixed(2)} ₺ altına inince haber vereceğiz` : 'Fiyat düşünce haber vereceğiz');
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const remove = async () => {
    if (!alert) return;
    setBusy(true);
    try { await api.deleteAlert(alert.id); onChange(null, 'Takip bırakıldı'); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' }} onPress={onClose} />
      <View style={{ backgroundColor: t.background, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, paddingBottom: 20 + insets.bottom, gap: 12 }}>
        <Text style={{ color: t.text, fontSize: 18, fontWeight: '800' }}>🔔 Fiyatını takip et</Text>
        {product ? (
          <Muted>Seçtiğin ürün takip edilecek: <Text style={{ color: t.text, fontWeight: '700' }}>{product.label}</Text>, şu an {product.price.toFixed(2)} ₺. Fiyatı düşünce Alarmlar sekmesinde haber veririz.</Muted>
        ) : (
          <Muted>{groupName} şu an en ucuz {cheapest != null ? `${cheapest.toFixed(2)} ₺` : '-'}. Hangi marka olursa olsun en ucuz fiyat düşünce haber veririz. Belli bir markayı takip etmek için önce listeden o satıra dokun.</Muted>
        )}

        <Pressable onPress={() => save(false)} disabled={busy}
          style={{ padding: 14, borderRadius: 12, borderWidth: 1, borderColor: t.border, backgroundColor: t.card, gap: 2 }}>
          <Text style={{ color: t.tint, fontWeight: '700' }}>Fiyatı düşünce haber ver</Text>
          <Muted>{product ? 'Şu anki fiyatının altına inince' : 'Şu anki en ucuz fiyatın altına inince'}</Muted>
        </Pressable>

        <View style={{ padding: 14, borderRadius: 12, borderWidth: 1, borderColor: t.border, backgroundColor: t.card, gap: 8 }}>
          <Text style={{ color: t.text, fontWeight: '700' }}>Şu fiyatın altına inince</Text>
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <View style={{ flex: 1 }}><Input placeholder="örn. 30,00" value={target} onChangeText={setTarget} keyboardType="decimal-pad" /></View>
            <Button title="Kur" onPress={() => save(true)} busy={busy} disabled={!target.trim()} />
          </View>
        </View>

        {error && <Text style={{ color: t.danger }}>{error}</Text>}
        {alert && <Text onPress={remove} style={{ color: t.danger, textAlign: 'center', padding: 6 }}>Takibi bırak</Text>}
      </View>
    </Modal>
  );
}
