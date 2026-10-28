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
export type PlanType = 'single_market' | 'combination' | 'opportunist';
export interface AssignedProduct {
  market_id: number | null; product_id: number | null; product_name: string | null; brand: string | null;
  unit_price: Money | null; store_id: number | null; store_name: string | null;
}
export interface ListItem {
  id: number; group_id: number; group_name: string; category_id: number | null; image_url: string | null;
  quantity: Money; preferred_brand: string | null; preferred_product_id: number | null; is_checked: boolean;
  position: number; note: string | null; assigned: AssignedProduct | null;
  added_by_id: number | null; added_by_name: string | null;
}
export interface ShoppingGroup { market_id: number | null; item_ids: number[]; checked_count: number; }
export interface ListSummary {
  id: number; owner_id: number; owner_name: string | null; member_count: number; name: string; icon: string | null;
  status: 'active' | 'shopping' | 'completed'; applied_plan: PlanType | null; planned_total: Money | null;
  item_count: number; checked_count: number; created_at: string; updated_at: string;
  estimated_total: Money | null; top_market_id: number | null;
}
export interface ListDetail extends ListSummary {
  preference_total: Money | null; expected_savings: Money | null; applied_at: string | null;
  completed_at: string | null; items: ListItem[]; shopping_groups: ShoppingGroup[]; share_code: string | null;
  members: ListMember[]; // ortak listeye kodla katılanlar (sahip hariç)
}
export interface ListMember { user_id: number; name: string | null; joined_at: string; }
export interface PlanLine {
  item_id: number; group_id: number; group_name: string; quantity: Money; product_id: number;
  product_name: string; brand: string | null; market_id: number; unit_price: Money; store_id: number | null;
  line_total: Money; substituted: boolean;
}
export interface MarketBreakdown { market_id: number; total: Money; item_ids: number[]; }
export interface Plan { plan_type: PlanType; total: Money; lines: PlanLine[]; missing_item_ids: number[]; by_market: MarketBreakdown[]; }
export interface MarketTotal { market_id: number; total: Money; found: number; missing: number; substituted: number; }
export interface OptimizeResult {
  single_market: { available: boolean; warning: string | null; plan: Plan | null; markets: MarketTotal[] };
  combination: Plan; opportunist: Plan;
  savings: { preference_total: Money; opportunist_total: Money; weekly: Money; monthly: Money; yearly: Money };
}
export interface CompleteResponse {
  list_id: number; saved_amount: Money; vault_total: Money; note: string | null; shopping_savings: Money;
}
export type ItemPatch = Partial<{ quantity: number; is_checked: boolean; preferred_product_id: number | null; preferred_brand: string | null }>;
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

export type FamilyMember = { user_id: number; name: string; is_owner: boolean; joined_at: string };
export type Family = {
  id: number; name: string; owner_id: number; invite_code: string; members: FamilyMember[];
  pending_invites: string[]; month_saved: Money; max_members: number;
};
export type FamilyInvite = { id: number; family_name: string; invited_by: string | null };
// Aile üyeleri birbirinin bütün listelerini kodsuz görür; ailesi yoksa bana gelen davetler
export type MyFamily = { family: Family | null; invites: FamilyInvite[] };

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
  lists: () => request<ListSummary[]>('GET', '/lists'),
  list: (id: number) => request<ListDetail>('GET', '/lists/' + id),
  createList: (name: string) => request<ListDetail>('POST', '/lists', { name }),
  deleteList: (id: number) => request<void>('DELETE', '/lists/' + id),
  addItem: (listId: number, groupId: number, preferredProductId?: number | null) =>
    request<ListDetail>('POST', `/lists/${listId}/items`, { group_id: groupId, preferred_product_id: preferredProductId ?? null }),
  updateItem: (listId: number, itemId: number, patch: ItemPatch) =>
    request<ListDetail>('PATCH', `/lists/${listId}/items/${itemId}`, patch),
  removeItem: (listId: number, itemId: number) => request<ListDetail>('DELETE', `/lists/${listId}/items/${itemId}`),
  optimize: (listId: number) => request<OptimizeResult>('GET', `/lists/${listId}/optimize`),
  applyPlan: (listId: number, plan_type: PlanType) => request<ListDetail>('POST', `/lists/${listId}/apply`, { plan_type }),
  cancelPlan: (listId: number) => request<ListDetail>('DELETE', `/lists/${listId}/plan`),
  complete: (listId: number) => request<CompleteResponse>('POST', `/lists/${listId}/complete`),
  // Ortak liste: sahip davet kodu alır, aile üyesi kodla katılır; üye kendini, sahip herkesi çıkarabilir
  shareList: (listId: number) => request<{ share_code: string }>('POST', `/lists/${listId}/share`),
  joinList: (code: string) => request<ListDetail>('POST', '/lists/join', { code }),
  removeMember: (listId: number, userId: number) => request<void>('DELETE', `/lists/${listId}/members/${userId}`),
  productGroup: (id: number) => request<GroupDetail>('GET', '/products/' + id),
  deals: () => request<Deal[]>('GET', '/products/deals'),
  myStores: () => request<Store[]>('GET', '/me/stores'),
  family: () => request<MyFamily>('GET', '/family'),
  createFamily: (name: string) => request<MyFamily>('POST', '/family', { name }),
  joinFamily: (code: string) => request<MyFamily>('POST', '/family/join', { code }),
  inviteToFamily: (email: string) => request<MyFamily>('POST', '/family/invites', { email }),
  acceptFamilyInvite: (id: number) => request<MyFamily>('POST', '/family/invites/' + id + '/accept'),
  declineFamilyInvite: (id: number) => request<void>('DELETE', '/family/invites/' + id),
  removeFamilyMember: (userId: number) => request<void>('DELETE', '/family/members/' + userId),
};
