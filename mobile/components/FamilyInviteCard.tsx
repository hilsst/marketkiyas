import { useState } from 'react';
import { Text, View } from 'react-native';

import { Button, Card, Muted, useTheme } from '@/components/ui';
import { api, FamilyInvite, MyFamily } from '@/lib/api';

/** E-postayla gelen aile daveti: kabul edince ailedeki herkesin listeleri görünür. */
export default function FamilyInviteCard({ invite, onDone }: { invite: FamilyInvite; onDone: (f: MyFamily) => void }) {
  const t = useTheme();
  const [busy, setBusy] = useState<'accept' | 'decline' | null>(null);
  const [error, setError] = useState<string | null>(null);

  const act = async (kind: 'accept' | 'decline') => {
    setError(null);
    setBusy(kind);
    try {
      if (kind === 'accept') onDone(await api.acceptFamilyInvite(invite.id));
      else {
        await api.declineFamilyInvite(invite.id);
        onDone(await api.family());
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card style={{ gap: 10, borderColor: t.tint, borderWidth: 2 }}>
      <Text style={{ color: t.text, fontSize: 16, fontWeight: '800' }}>👨‍👩‍👧 Ailene katılmaya davet edildin</Text>
      <Muted>
        {invite.invited_by ? `${invite.invited_by} seni ` : 'Seni '}“{invite.family_name}” ailesine çağırıyor. Katılınca ailedeki
        herkesin listelerini görür, kod paylaşmadan ürün eklersiniz.
      </Muted>
      {error && <Text style={{ color: t.danger }}>{error}</Text>}
      <View style={{ flexDirection: 'row', gap: 8 }}>
        <View style={{ flex: 1 }}><Button title="Katıl" onPress={() => act('accept')} busy={busy === 'accept'} disabled={!!busy} /></View>
        <View style={{ flex: 1 }}><Button title="Hayır" kind="secondary" onPress={() => act('decline')} busy={busy === 'decline'} disabled={!!busy} /></View>
      </View>
    </Card>
  );
}
