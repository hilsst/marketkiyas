import { api, ApiError, formatSize, num, setApiToken, setUnauthorizedHandler } from '@/lib/api';
import { newDeviceId, setDeviceId } from '@/lib/device';

jest.mock('expo-secure-store', () => ({ getItemAsync: jest.fn(), setItemAsync: jest.fn(), deleteItemAsync: jest.fn() }));

const ok = (body: unknown, status = 200) =>
  Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) } as Response);

afterEach(() => { setApiToken(null); setDeviceId(null); jest.restoreAllMocks(); });

test('istek oturum anahtarını ve cihaz kimliğini başlık olarak taşır', async () => {
  const fetchMock = jest.spyOn(globalThis, 'fetch').mockReturnValue(ok([]));
  setApiToken('tok');
  setDeviceId('dev-12345678');
  await api.lists();
  const [url, init] = fetchMock.mock.calls[0];
  expect(String(url)).toMatch(/\/lists$/);
  expect(init?.headers).toMatchObject({ Authorization: 'Bearer tok', 'X-Device-Id': 'dev-12345678' });
});

test('misafir isteğinde Authorization yok', async () => {
  const fetchMock = jest.spyOn(globalThis, 'fetch').mockReturnValue(ok([]));
  await api.markets();
  expect((fetchMock.mock.calls[0][1]?.headers as Record<string, string>).Authorization).toBeUndefined();
});

test('sunucu hata mesajı ApiError olur', async () => {
  jest.spyOn(globalThis, 'fetch').mockReturnValue(ok({ detail: 'Bu e-posta ile kayıtlı bir hesap var' }, 409));
  await expect(api.register('a@b.co', 'sifre1234')).rejects.toMatchObject({ message: 'Bu e-posta ile kayıtlı bir hesap var', status: 409 });
});

test('ağ hatası anlaşılır mesaj verir', async () => {
  jest.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Network request failed'));
  const err = await api.markets().catch(e => e);
  expect(err).toBeInstanceOf(ApiError);
  expect(err.status).toBe(0);
});

test('401 ve oturum açıkken çıkış işleyicisi çağrılır', async () => {
  const onOut = jest.fn();
  setUnauthorizedHandler(onOut);
  setApiToken('eski');
  jest.spyOn(globalThis, 'fetch').mockReturnValue(ok({ detail: 'Oturum geçersiz' }, 401));
  await expect(api.lists()).rejects.toBeInstanceOf(ApiError);
  expect(onOut).toHaveBeenCalledTimes(1);
  setUnauthorizedHandler(null);
});

test('boyut ve fiyat yardımcıları', () => {
  expect(formatSize('1000', 'ml')).toBe('1 L');
  expect(formatSize('500', 'g')).toBe('500 g');
  expect(formatSize('1500', 'g')).toBe('1,5 kg');
  expect(formatSize('15', 'adet')).toBe('15 adet');
  expect(formatSize(null, null)).toBe('');
  expect(num('32.50')).toBe(32.5);
  expect(num(null)).toBe(0);
});

test('cihaz kimliği sunucunun kabul ettiği biçimde', () => {
  for (let i = 0; i < 50; i++) expect(newDeviceId()).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
});
