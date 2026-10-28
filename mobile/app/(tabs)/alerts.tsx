import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';

import MarketBadge from '@/components/MarketBadge';
import ProductImage from '@/components/ProductImage';
import { Card, LoginPrompt, Muted, Screen, Title, useTheme } from '@/components/ui';
import { api, formatSize, num, PriceAlert } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { useCatalog } from '@/lib/catalog';

/**
 * Takip ettiğim ürünler: fiyatı düşenler üstte. Sekme açılınca yeni düşüşler "görüldü" sayılır.
 * Telefona bildirim 7. adımda gelecek.
 */
export default function AlertsScreen() {
  const t = useTheme();
  const { user } = useAuth();
  const { categoryIcon } = useCatalog();
  const [alerts, setAlerts] = useState<PriceAlert[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useFocusEffect(useCallback(() => {
    if (!user) return;
    api.alerts()
      .then(all => {
        setAlerts([...all].sort((a, b) => Number(b.triggered) - Number(a.triggered)));
        setError(null);
        if (all.some(a => a.unread)) api.markAlertsSeen().catch(() => {});
      })
      .catch(e => setError((e as Error).message));
  }, [user]));

  const remove = async (id: number) => {
    try {
      await api.deleteAlert(id);
      setAlerts(prev => prev?.filter(a => a.id !== id) ?? null);
    } catch (e) { setError((e as Error).message); }
  };

  return (
    <Screen>
      <Title>🔔 Alarmlar</Title>
      {!user ? <LoginPrompt what="Ürün takip etmek" /> : (
        <>
          <Muted>Takip ettiğin ürünlerin fiyatı düşünce burada görünür. Ürün sayfasındaki 🔔 Takip et ile ekleyebilirsin.</Muted>
          {error && <Text style={{ color: t.danger }}>{error}</Text>}
          {alerts === null && !error && <ActivityIndicator color={t.tint} style={{ marginTop: 24 }} />}
          {alerts?.length === 0 && (
            <Card style={{ alignItems: 'center', gap: 6, padding: 24 }}>
              <Text style={{ fontSize: 30 }}>🔔</Text>
              <Text style={{ color: t.text }}>Henüz takip ettiğin ürün yok</Text>
              <Muted style={{ textAlign: 'center' }}>Bir ürünü açıp 🔔 Takip et&apos;e dokun.</Muted>
            </Card>
          )}
          {alerts?.map(a => {
            const current = a.current_price != null ? num(a.current_price) : null;
            const threshold = a.target_price != null ? num(a.target_price) : a.baseline_price != null ? num(a.baseline_price) : null;
            return (
              <Pressable key={a.id} onPress={() => router.push({ pathname: '/product/[id]', params: { id: String(a.group_id) } })}>
                <Card style={{ flexDirection: 'row', gap: 12, alignItems: 'center', borderColor: a.triggered ? t.tint : t.border, borderWidth: a.triggered ? 2 : 1 }}>
                  <ProductImage uri={a.image_url} icon={categoryIcon(a.category_id)} size={56} />
                  <View style={{ flex: 1, gap: 3 }}>
                    {a.triggered && <Text style={{ color: t.tint, fontSize: 12, fontWeight: '800' }}>📉 FİYATI DÜŞTÜ{a.unread ? ' · YENİ' : ''}</Text>}
                    <Text style={{ color: t.text, fontWeight: '700' }} numberOfLines={2}>{a.group_name}</Text>
                    <Muted>
                      {formatSize(a.quantity, a.unit) ? `${formatSize(a.quantity, a.unit)} · ` : ''}
                      {a.target_price != null ? `${num(a.target_price).toFixed(2)} ₺ altına inince` : threshold != null ? `${threshold.toFixed(2)} ₺ altına inince` : 'Fiyat düşünce'}
                    </Muted>
                    {current != null && (
                      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                        {a.current_market_id != null && <MarketBadge id={a.current_market_id} size={18} />}
                        <Text style={{ color: a.triggered ? t.tint : t.text, fontWeight: '800' }}>Şu an {current.toFixed(2)} ₺</Text>
                      </View>
                    )}
                  </View>
                  <Text onPress={() => remove(a.id)} style={{ color: t.danger, padding: 6 }}>Bırak</Text>
                </Card>
              </Pressable>
            );
          })}
        </>
      )}
    </Screen>
  );
}
