jest.mock('expo-constants', () => ({ __esModule: true, default: { expoConfig: { hostUri: 'localhost:8081' } } }));

import { api, ApiError, setApiToken, setUnauthorizedHandler } from '@/lib/api';

const ok = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body }) as Response;

describe('guest and trust endpoints', () => {
  const calls: { url: string; init: RequestInit }[] = [];
  beforeEach(() => {
    calls.length = 0;
    setApiToken(null);
    global.fetch = jest.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      calls.push({ url: String(url), init: init ?? {} });
      return ok({ ok: true });
    }) as unknown as typeof fetch;
  });

  it('starts a guest without credentials', async () => {
    await api.guest();
    expect(calls[0].url).toMatch(/\/auth\/guest$/);
    expect(calls[0].init.method).toBe('POST');
    expect(calls[0].init.body).toBeUndefined();
  });

  it('upgrades the guest with the guest token', async () => {
    setApiToken('guest-token');
    await api.upgrade(' me@x.co ', 'sifre-12345', 'Ayşe');
    const { url, init } = calls[0];
    expect(url).toMatch(/\/auth\/upgrade$/);
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer guest-token');
    expect(JSON.parse(init.body as string)).toEqual({ email: ' me@x.co ', password: 'sifre-12345', full_name: 'Ayşe' });
  });

  it('reports a wrong price for a product and store', async () => {
    await api.reportPrice(5, { product_id: 9, store_id: 2, reported_price: 45.5, note: 'kasada' });
    expect(calls[0].url).toMatch(/\/products\/5\/price-reports$/);
    expect(JSON.parse(calls[0].init.body as string)).toEqual({ product_id: 9, store_id: 2, reported_price: 45.5, note: 'kasada' });
  });

  it('sends preferred deal ingredients when creating a plan', async () => {
    await api.createMealPlan({ period: 'weekly', servings: 2, meal_slots: ['aksam'], courses: ['ana'], prefer: ['Tavuk göğsü'] });
    expect(JSON.parse(calls[0].init.body as string).prefer).toEqual(['Tavuk göğsü']);
    await api.dealIngredients();
    expect(calls[1].url).toMatch(/\/deal-menu\/ingredients$/);
  });

  it('turns a 429 into a readable error', async () => {
    global.fetch = jest.fn(async () => ok({ detail: 'Bugün için bildirim sınırına ulaştın' }, 429)) as unknown as typeof fetch;
    await expect(api.reportPrice(1, { product_id: 1 })).rejects.toMatchObject({ status: 429, message: expect.stringContaining('sınırına') });
    await expect(api.reportPrice(1, { product_id: 1 })).rejects.toBeInstanceOf(ApiError);
  });

  it('keeps the guest session when a login attempt fails with 401', async () => {
    const dropped = jest.fn();
    setUnauthorizedHandler(dropped);
    setApiToken('guest-token');
    global.fetch = jest.fn(async () => ok({ detail: 'E-posta veya şifre hatalı' }, 401)) as unknown as typeof fetch;
    await expect(api.login('a@b.co', 'yanlis')).rejects.toMatchObject({ status: 401 });
    expect(dropped).not.toHaveBeenCalled();
    // Ama süresi dolmuş anahtarla yapılan normal istek oturumu düşürür
    await expect(api.lists()).rejects.toMatchObject({ status: 401 });
    expect(dropped).toHaveBeenCalledTimes(1);
    setUnauthorizedHandler(null);
  });
});
