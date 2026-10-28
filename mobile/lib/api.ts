/**
 * MarketKıyas sunucusu (FastAPI) istemcisi. Uçlar ve şemalar web arayüzüyle aynıdır
 * (frontend/src/lib/api.ts); burada telefonun kullandıkları tanımlıdır.
 *
 * Adres EXPO_PUBLIC_API_URL ile verilir. Geliştirmede telefon aynı Wi-Fi'deki bilgisayara
 * web arayüzünün /api vekili üzerinden bağlanır (BASLAT.bat: http://<bilgisayar-ip>:3000/api).
 */

export const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.68.119:3000/api';

export type Money = string; // sunucu Decimal'leri metin gönderir: "32.50"
export type Unit = 'ml' | 'g' | 'adet';

export interface User { id: number; email: string; full_name: string | null; has_password: boolean; }
export interface AuthResponse { access_token: string; token_type: string; expires_in: number; user: User; }
export interface Market { id: number; slug: string; name: string; color: string | null; logo_url: string | null; }
export interface Category { id: number; slug: string; name: string; icon: string | null; parent_id: number | null; }
export interface MarketPrice { market_id: number; min_price: Money; regular_price: Money | null; }
export interface GroupSummary {
  id: number; name: string; category_id: number | null; subcategory_id?: number | null;
  quantity: Money | null; unit: Unit | null; image_url: string | null; min_price: Money | null;
  market_prices: MarketPrice[]; brands: string[];
}
export interface PricePoint { price: Money; recorded_at: string; }
export interface GroupProduct {
  id: number; name: string; brand: string | null; market_id: number; price: Money | null; regular_price: Money | null;
  store_id: number | null; store_name: string | null; is_available: boolean; image_url: string | null;
  price_history: PricePoint[]; store_prices: { store_id: number; store_name: string; price: Money }[];
}
export interface GroupDetail extends GroupSummary { products: GroupProduct[]; }
export interface Deal {
  group_id: number; group_name: string; category_id: number | null; image_url: string | null;
  quantity: Money | null; unit: Unit | null; product_id: number; product_name: string; brand: string | null;
  market_id: number; store_id: number | null; price: Money; previous_price: Money; discount_percent: number; is_campaign: boolean;
}
export interface Store {
  id: number; name: string; market_id: number; market_slug: string; market_name: string;
  latitude: Money | null; longitude: Money | null; distance_km: number | null; selected: boolean;
}
export interface SavingsRecord { id: number; list_name: string; saved_amount: Money; created_at: string; }
export interface SavingsVault { total_saved: Money; record_count: number; records: SavingsRecord[]; }

export class ApiError extends Error {
  constructor(message: string, readonly status: number) { super(message); }
}

let token: string | null = null;
let onUnauthorized: (() => void) | null = null;

/** Oturum değişince auth katmanı çağırır; her istek bu anahtarı taşır. */
export function setApiToken(value: string | null) { token = value; }
export function setUnauthorizedHandler(fn: (() => void) | null) { onUnauthorized = fn; }

const qs = (params: Record<string, string | number | null | undefined>) => {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  return parts.length ? '?' + parts.join('&') : '';
};

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(API_URL + path, {
      method,
      headers: {
        Accept: 'application/json',
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError('Sunucuya ulaşılamadı. İnternet bağlantınızı kontrol edin.', 0);
  }
  if (res.status === 401 && token) onUnauthorized?.();
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const detail = data?.detail;
    const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail[0]?.msg : null;
    throw new ApiError(message || `İstek başarısız (${res.status})`, res.status);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const num = (v: Money | number | null | undefined) => (v == null ? 0 : Number(v));

export function formatSize(quantity: Money | null, unit: Unit | null): string {
  if (quantity == null || unit == null) return '';
  const q = num(quantity);
  const fmt = (n: number) => String(Number(n.toFixed(2))).replace('.', ',');
  if (unit === 'ml') return q >= 1000 ? `${fmt(q / 1000)} L` : `${fmt(q)} ml`;
  if (unit === 'g') return q >= 1000 ? `${fmt(q / 1000)} kg` : `${fmt(q)} g`;
  return `${fmt(q)} adet`;
}

export const api = {
  register: (email: string, password: string, full_name?: string) =>
    request<AuthResponse>('POST', '/auth/register', { email, password, full_name: full_name || null }),
  login: (email: string, password: string) => request<AuthResponse>('POST', '/auth/login', { email, password }),
  me: () => request<User>('GET', '/auth/me'),
  requestPasswordReset: (email: string) => request<{ detail: string }>('POST', '/auth/password-reset/request', { email }),
  confirmPasswordReset: (email: string, code: string, new_password: string) =>
    request<AuthResponse>('POST', '/auth/password-reset/confirm', { email, code, new_password }),
  deleteAccount: (password?: string) => request<void>('DELETE', '/auth/me', { password: password || null }),
  markets: () => request<Market[]>('GET', '/markets'),
  categories: () => request<Category[]>('GET', '/categories'),
  searchProducts: (q: string, categoryId?: number | null, opts: { sort?: 'name' | 'popular'; limit?: number; subcategoryId?: number | null } = {}) =>
    request<GroupSummary[]>('GET', '/products' + qs({
      q, category_id: categoryId, subcategory_id: opts.subcategoryId, limit: opts.limit ?? 50, sort: opts.sort,
    })),
  savings: () => request<SavingsVault>('GET', '/savings'),
  productGroup: (id: number) => request<GroupDetail>('GET', '/products/' + id),
  deals: () => request<Deal[]>('GET', '/products/deals'),
  myStores: () => request<Store[]>('GET', '/me/stores'),
};
