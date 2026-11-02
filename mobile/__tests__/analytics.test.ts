import { createAnalytics, QueuedEvent, screenName } from '@/lib/analytics';
import { setDeviceId } from '@/lib/device';

jest.mock('expo-secure-store', () => ({ getItemAsync: jest.fn(), setItemAsync: jest.fn(), deleteItemAsync: jest.fn() }));

const fixedNow = () => new Date('2026-11-02T12:00:00Z');

beforeEach(() => { jest.useFakeTimers(); setDeviceId('dev-12345678'); });
afterEach(() => { jest.useRealTimers(); setDeviceId(null); });

test('olaylar 20 olunca topluca gider', async () => {
  const send = jest.fn().mockResolvedValue(true);
  const a = createAnalytics({ send, now: fixedNow });
  for (let i = 0; i < 19; i++) a.track('screen_view', { screen: '/' });
  expect(send).not.toHaveBeenCalled();
  a.track('app_open');
  await a.flush();
  expect(send).toHaveBeenCalledTimes(1);
  const [id, events] = send.mock.calls[0] as [string, QueuedEvent[]];
  expect(id).toBe('dev-12345678');
  expect(events).toHaveLength(20);
  expect(events[0]).toEqual({ name: 'screen_view', at: '2026-11-02T12:00:00.000Z', props: { screen: '/' } });
  expect(a.pending()).toBe(0);
});

test('10 sn sonra az olay da gönderilir', async () => {
  const send = jest.fn().mockResolvedValue(true);
  const a = createAnalytics({ send, now: fixedNow });
  a.track('app_open');
  expect(send).not.toHaveBeenCalled();
  await jest.advanceTimersByTimeAsync(10_000);
  expect(send).toHaveBeenCalledTimes(1);
  expect(a.pending()).toBe(0);
});

test('gönderilemeyen olaylar kalır, sonra yeniden denenir', async () => {
  const send = jest.fn().mockResolvedValueOnce(false).mockResolvedValue(true);
  const a = createAnalytics({ send, now: fixedNow });
  a.track('app_open');
  await a.flush();
  expect(a.pending()).toBe(1);
  await jest.advanceTimersByTimeAsync(10_000);
  expect(send).toHaveBeenCalledTimes(2);
  expect(a.pending()).toBe(0);
});

test('cihaz kimliği yokken gönderilmez', async () => {
  setDeviceId(null);
  const send = jest.fn().mockResolvedValue(true);
  const a = createAnalytics({ send, now: fixedNow });
  a.track('app_open');
  await a.flush();
  expect(send).not.toHaveBeenCalled();
  expect(a.pending()).toBe(1);
});

test('kuyruk 200 olayla sınırlı, paketler en çok 50 olay', async () => {
  const send = jest.fn().mockResolvedValue(false);
  const a = createAnalytics({ send, now: fixedNow });
  for (let i = 0; i < 230; i++) a.track('screen_view', { n: i });
  await a.flush();
  expect(a.pending()).toBe(200);
  send.mockResolvedValue(true);
  await a.flush();
  expect(a.pending()).toBe(0);
  const sizes = send.mock.calls.slice(-4).map(c => (c[1] as QueuedEvent[]).length);
  expect(sizes).toEqual([50, 50, 50, 50]);
});

test('ekran adından kimlik çıkarılır', () => {
  expect(screenName('/meals/12')).toBe('/meals/[id]');
  expect(screenName('/recipe/7/')).toBe('/recipe/[id]/');
  expect(screenName('/')).toBe('/');
  expect(screenName('/(tabs)/lists')).toBe('/(tabs)/lists');
});
