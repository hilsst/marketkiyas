/**
 * Uygulama analitiği (Faz 1 huni ölçümü). Huninin adımlarını (plan kurma, listeye aktarma, alışveriş)
 * sunucu kendisi kaydeder; burada sunucunun göremediği olaylar toplanır: uygulama açılışı ve ekran görüntüleme.
 * Olaylar bellekte birikir, 20 olunca ya da 10 sn sonra POST /api/events ile toplu gider; gönderilemezse
 * sonraki seferde yeniden denenir (en çok 200 olay tutulur). Kişisel veri (e-posta, ad) gönderilmez.
 */
import { API_URL } from '@/lib/api';
import { getDeviceId, initDeviceId } from '@/lib/device';

export type EventProps = Record<string, string | number | boolean | null>;
export interface QueuedEvent { name: string; at: string; props?: EventProps }

const BATCH = 20;
const MAX_QUEUE = 200;
const MAX_SEND = 50; // sunucu tek pakette en çok 50 olay kabul eder
const FLUSH_MS = 10_000;

export interface AnalyticsDeps {
  send: (deviceId: string, events: QueuedEvent[]) => Promise<boolean>;
  now: () => Date;
}

export function createAnalytics(deps: AnalyticsDeps) {
  let queue: QueuedEvent[] = [];
  let timer: ReturnType<typeof setTimeout> | null = null;
  let flushing: Promise<void> | null = null;

  const schedule = () => {
    if (timer) return;
    timer = setTimeout(() => { timer = null; void flush(); }, FLUSH_MS);
  };

  async function flush(): Promise<void> {
    if (flushing) return flushing;
    if (timer) { clearTimeout(timer); timer = null; }
    flushing = (async () => {
      try {
        while (queue.length) {
          const id = getDeviceId();
          if (!id) return; // kimlik daha okunmadı; sonra denenir
          const chunk = queue.slice(0, MAX_SEND);
          if (!(await deps.send(id, chunk))) { schedule(); return; }
          queue = queue.slice(chunk.length);
        }
      } finally { flushing = null; }
    })();
    return flushing;
  }

  function track(name: string, props?: EventProps) {
    queue.push({ name, at: deps.now().toISOString(), ...(props ? { props } : {}) });
    if (queue.length > MAX_QUEUE) queue = queue.slice(queue.length - MAX_QUEUE);
    if (queue.length >= BATCH) void flush(); else schedule();
  }

  return { track, flush, pending: () => queue.length };
}

async function postEvents(deviceId: string, events: QueuedEvent[]): Promise<boolean> {
  try {
    const res = await fetch(API_URL + '/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'X-Device-Id': deviceId },
      body: JSON.stringify({ device_id: deviceId, events }),
    });
    // 4xx: paket bozuk, yeniden denemek işe yaramaz; at. 5xx / ağ hatası: tekrar denenir.
    return res.ok || (res.status >= 400 && res.status < 500);
  } catch {
    return false;
  }
}

const shared = createAnalytics({ send: postEvents, now: () => new Date() });

export const track = shared.track;
export const flushEvents = shared.flush;

/** Açılışta bir kez: cihaz kimliğini hazırlar, app_open yazar. */
export async function startAnalytics(): Promise<void> {
  await initDeviceId();
  track('app_open');
  void shared.flush();
}

/** "/meals/12" -> "/meals/[id]": ekran adı kimlik taşımasın, aynı ekran tek satırda toplansın. */
export function screenName(pathname: string): string {
  return pathname.replace(/\/\d+(?=\/|$)/g, '/[id]') || '/';
}
