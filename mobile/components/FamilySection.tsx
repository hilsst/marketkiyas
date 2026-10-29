import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { Alert, Platform, Pressable, Share, Text, View } from 'react-native';

import FamilyInviteCard from '@/components/FamilyInviteCard';
import { Button, Card, Input, Muted, useTheme } from '@/components/ui';
import { api, MyFamily, num, User } from '@/lib/api';

/**
 * Profil > Ailem. Aile üyeleri birbirinin bütün listelerini kod paylaşmadan görür ve düzenler.
 * Katılım bir kez: aile kodu (WhatsApp/SMS ile) ya da uygulamadaki kullanıcının e-postasına davet.
 */
export default function FamilySection({ user }: { user: User }) {
  const t = useTheme();
  const [data, setData] = useState<MyFamily | null>(null);
  const [mode, setMode] = useState<'create' | 'join' | null>(null);
  const [text, setText] = useState('');
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  useFocusEffect(useCallback(() => {
    api.family().then(setData).catch(() => setData(null));
  }, []));

  const run = async (fn: () => Promise<MyFamily | void>, done?: string) => {
    setError(null);
    setInfo(null);
    setBusy(true);
    try {
      const result = await fn();
      setData(result || await api.family());
      setMode(null);
      setText('');
      if (done) setInfo(done);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const confirm = (message: string, onYes: () => void) => {
    if (Platform.OS === 'web') { if (globalThis.confirm?.(message)) onYes(); return; }
    Alert.alert('Emin misin?', message, [{ text: 'Vazgeç', style: 'cancel' }, { text: 'Evet', style: 'destructive', onPress: onYes }]);
  };

  const family = data?.family;
  if (!data) return null;

  const header = <Text style={{ color: t.text, fontSize: 17, fontWeight: '800' }}>👨‍👩‍👧 Ailem</Text>;

  if (!family) {
    return (
      <View style={{ gap: 10 }}>
        {data.invites.map(inv => <FamilyInviteCard key={inv.id} invite={inv} onDone={setData} />)}
        <Card style={{ gap: 10 }}>
          {header}
          <Muted>Aileni kur: eşin ve çocukların senin bütün listelerini görür, markette olsan bile listeye kod paylaşmadan ürün ekleyebilir.</Muted>
          {mode === null && (
            <View style={{ flexDirection: 'row', gap: 8 }}>
              <View style={{ flex: 1 }}><Button title="Aile oluştur" onPress={() => { setMode('create'); setText(user.full_name ? `${user.full_name} ailesi` : ''); }} /></View>
              <View style={{ flex: 1 }}><Button title="Kodla katıl" kind="secondary" onPress={() => { setMode('join'); setText(''); }} /></View>
            </View>
          )}
          {mode === 'create' && (
            <>
              <Input placeholder="Aile adı (örn. Yılmaz ailesi)" value={text} onChangeText={setText} maxLength={80} />
              <Button title="Oluştur" onPress={() => run(() => api.createFamily(text.trim()))} busy={busy} disabled={!text.trim()} />
              <Button title="Vazgeç" kind="secondary" onPress={() => setMode(null)} />
            </>
          )}
          {mode === 'join' && (
            <>
              <Input placeholder="Aile kodu (8 harf)" value={text} onChangeText={v => setText(v.toUpperCase())} autoCapitalize="characters" maxLength={16} />
              <Button title="Aileye katıl" onPress={() => run(() => api.joinFamily(text.trim()))} busy={busy} disabled={text.trim().length < 4} />
              <Button title="Vazgeç" kind="secondary" onPress={() => setMode(null)} />
            </>
          )}
          {error && <Text style={{ color: t.danger }}>{error}</Text>}
        </Card>
      </View>
    );
  }

  const isOwner = family.owner_id === user.id;
  const full = family.members.length >= family.max_members;
  const shareCode = () => Share.share({
    message: `Ucuzu'da "${family.name}" ailemize katıl! Listelerimizi birlikte kullanalım. Profil > Ailem > "Kodla katıl" deyip bu kodu yaz: ${family.invite_code}`,
  });

  return (
    <Card style={{ gap: 10 }}>
      {header}
      <Text style={{ color: t.text, fontWeight: '700' }}>{family.name}</Text>
      <Muted>Ailedeki herkes birbirinin bütün listelerini görür ve ürün ekleyebilir.</Muted>
      <Text style={{ color: t.text }}>Bu ay ailece tasarruf: <Text style={{ fontWeight: '800', color: t.tint }}>{num(family.month_saved).toFixed(2)} ₺</Text></Text>

      <Text style={{ color: t.text, fontWeight: '700', marginTop: 4 }}>Üyeler ({family.members.length}/{family.max_members})</Text>
      {family.members.map(m => (
        <View key={m.user_id} style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <Text style={{ color: t.text }}>
            {m.name}{m.user_id === user.id ? ' (sen)' : ''}{m.is_owner ? ' · kurucu' : ''}
          </Text>
          {isOwner && m.user_id !== user.id && (
            <Pressable onPress={() => confirm(`${m.name} aileden çıkarılsın mı? Artık listelerinizi göremez.`,
              () => run(() => api.removeFamilyMember(m.user_id)))} hitSlop={8}>
              <Text style={{ color: t.danger }}>Çıkar</Text>
            </Pressable>
          )}
        </View>
      ))}
      {family.pending_invites.map(e => <Muted key={e}>✉️ {e} · davet bekliyor</Muted>)}

      {!full && (
        <>
          <Text style={{ color: t.text, fontWeight: '700', marginTop: 4 }}>Aileye kişi ekle</Text>
          <Muted>Aile kodu (bir kez girilir):</Muted>
          <Text selectable style={{ color: t.text, fontSize: 26, fontWeight: '900', letterSpacing: 4, textAlign: 'center' }}>{family.invite_code}</Text>
          <Button title="Kodu WhatsApp / SMS ile gönder" onPress={shareCode} />
          <Muted>{"ya da Ucuzu'ya üye olan kişinin e-postasını yaz, uygulamada daveti görsün:"}</Muted>
          <Input placeholder="ornek@eposta.com" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" autoComplete="email" />
          <Button title="Davet gönder" kind="secondary" busy={busy} disabled={!email.includes('@')}
            onPress={() => run(async () => { const r = await api.inviteToFamily(email.trim()); setEmail(''); return r; }, 'Davet gönderildi. Kişi uygulamayı açınca kabul edebilir.')} />
        </>
      )}
      {full && <Muted>Aile en fazla {family.max_members} kişi olabilir.</Muted>}
      {info && <Text style={{ color: t.tint }}>{info}</Text>}
      {error && <Text style={{ color: t.danger }}>{error}</Text>}

      <Text onPress={() => confirm('Aileden ayrılırsan ailenin listelerini artık göremezsin. Kendi listelerin sende kalır.',
        () => run(() => api.removeFamilyMember(user.id)))}
        style={{ color: t.danger, textAlign: 'center', padding: 6 }}>Aileden ayrıl</Text>
    </Card>
  );
}
