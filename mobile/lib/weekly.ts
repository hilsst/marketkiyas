/**
 * Haftalık menü bildirimi: "Bu haftanın menüsü hazır: 1.240 TL". Telefonda yerel bildirimdir (sunucu
 * gerekmez); her pazar 11:00'de tekrarlanır. Metin sabit gittiği için son planın tutarı her plan
 * kaydında ve uygulama açılışında yeniden kurulur (reschedule).
 */
import { requireOptionalNativeModule } from 'expo';
import Constants, { ExecutionEnvironment } from 'expo-constants';
import { Platform } from 'react-native';

import { loadFlag, saveFlag } from '@/lib/session';

export const WEEKLY_FLAG = 'ucuzu.weekly-menu';
export const WEEKLY_WEEKDAY = 1; // expo-notifications: 1 = Pazar
export const WEEKLY_HOUR = 11;

export function weeklyContent(total?: number | null) {
  const cost = total != null && total > 0
    ? `: ${Math.round(total).toLocaleString('tr-TR')} TL`
    : '. Bütçene göre kur, en ucuza al.';
  return {
    title: 'Ucuzu',
    body: total != null && total > 0 ? `Bu haftanın menüsü hazır${cost}` : `Bu haftanın menüsünü kur${cost}`,
    data: { url: '/meals' },
  };
}

// Expo Go'da expo-notifications'ın yerel parçası eksik olabilir ("Cannot find native module"): paketi yüklemeden
// önce Android'de o parçanın var olup olmadığına bakılır; yoksa özellik kapalı kalır.
function notificationsAvailable(): boolean {
  if (Platform.OS === 'web') return false;
  if (Constants.executionEnvironment === ExecutionEnvironment.StoreClient) return false;
  if (Platform.OS !== 'android') return true;
  try { return requireOptionalNativeModule('ExpoTopicSubscriptionModule') != null; } catch { return false; }
}
export const weeklySupported = notificationsAvailable();

export async function isWeeklyOn(): Promise<boolean> {
  return (await loadFlag(WEEKLY_FLAG)) === '1';
}

/** Açar: izin ister (Android 13+ ve iOS'ta tam bu anda sorulur), reddedilirse false. */
export async function enableWeekly(total?: number | null): Promise<boolean> {
  if (!weeklySupported) return false;
  const Notifications = await import('expo-notifications');
  await ensureChannel(Notifications);
  let { status } = await Notifications.getPermissionsAsync();
  if (status !== 'granted') status = (await Notifications.requestPermissionsAsync()).status;
  if (status !== 'granted') return false;
  await schedule(total);
  await saveFlag(WEEKLY_FLAG, '1');
  return true;
}

export async function disableWeekly(): Promise<void> {
  await saveFlag(WEEKLY_FLAG, null);
  if (!weeklySupported) return;
  const Notifications = await import('expo-notifications');
  await Notifications.cancelAllScheduledNotificationsAsync();
}

/** Plan kaydedilince ve uygulama açılınca: açıksa bildirimi güncel tutarla yeniden kurar. */
export async function rescheduleWeekly(total?: number | null): Promise<void> {
  if (!weeklySupported || !(await isWeeklyOn())) return;
  await schedule(total);
}

const CHANNEL = 'weekly-menu';

/** Android 13+ izin penceresi, bildirim kanalı oluşturulmadan açılmaz */
async function ensureChannel(Notifications: typeof import('expo-notifications')) {
  if (Platform.OS !== 'android') return;
  await Notifications.setNotificationChannelAsync(CHANNEL, {
    name: 'Haftalık menü', importance: Notifications.AndroidImportance.DEFAULT,
  });
}

async function schedule(total?: number | null) {
  const Notifications = await import('expo-notifications');
  await ensureChannel(Notifications);
  await Notifications.cancelAllScheduledNotificationsAsync();
  await Notifications.scheduleNotificationAsync({
    content: weeklyContent(total),
    trigger: {
      type: Notifications.SchedulableTriggerInputTypes.WEEKLY,
      weekday: WEEKLY_WEEKDAY, hour: WEEKLY_HOUR, minute: 0, channelId: CHANNEL,
    },
  });
}

let handledCold = false; // soğuk açılış dokunuşu yalnız bir kez işlenir

/** Bildirime dokununca planlayıcı açılır. Kök düzende bir kez bağlanır; döndürülen işlev dinleyiciyi söker. */
export function listenWeeklyTaps(open: (url: string) => void): () => void {
  if (!weeklySupported) return () => {};
  let remove: (() => void) | undefined;
  let cancelled = false;
  void import('expo-notifications').then(N => {
    if (cancelled) return;
    N.setNotificationHandler({
      handleNotification: async () => ({ shouldShowBanner: true, shouldShowList: true, shouldPlaySound: false, shouldSetBadge: false }),
    });
    const sub = N.addNotificationResponseReceivedListener(r => {
      const url = r.notification.request.content.data?.url;
      if (typeof url === 'string') open(url);
    });
    remove = () => sub.remove();
    // Uygulama bildirime dokunularak soğuk açıldıysa dinleyici o dokunuşu kaçırır; son yanıtı da kontrol et
    void N.getLastNotificationResponseAsync().then(r => {
      const url = r?.notification.request.content.data?.url;
      if (!cancelled && typeof url === 'string' && !handledCold) { handledCold = true; open(url); }
    });
  }).catch(() => {});
  return () => { cancelled = true; remove?.(); };
}
