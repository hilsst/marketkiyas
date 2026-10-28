// MarketKıyas FastAPI istemcisi. Tutarlar API'den string (Decimal) gelir; `num` ile sayıya çevrilir.

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const TOKEN_KEY = "mk_token";

export type Money = string;
export type PlanType = "single_market" | "combination" | "opportunist";
export type Unit = "ml" | "g" | "adet";

export interface User { id: number; email: string; full_name: string | null; created_at: string; }
export interface AuthResponse { access_token: string; token_type: string; expires_in: number; user: User; }

export interface Market { id: number; slug: string; name: string; color: string | null; logo_url: string | null; }
export interface Category { id: number; slug: string; name: string; icon: string | null; parent_id: number | null; }

export interface MarketPrice { market_id: number; min_price: Money; regular_price: Money | null; }
export interface GroupSummary {
  id: number; name: string; category_id: number | null; subcategory_id?: number | null; quantity: Money | null; unit: Unit | null;
  image_url: string | null; min_price: Money | null; market_prices: MarketPrice[]; brands: string[];
}
export interface PricePoint { price: Money; recorded_at: string; }
export interface GroupProduct {
  id: number; name: string; brand: string | null; market_id: number; price: Money | null;
  regular_price: Money | null; store_id: number | null; store_name: string | null; is_available: boolean;
  image_url: string | null; price_history: PricePoint[];
  store_prices: { store_id: number; store_name: string; price: Money }[]; // seçili şubeler, ucuzdan pahalıya
}
export interface GroupDetail extends GroupSummary { products: GroupProduct[]; }

export interface AssignedProduct {
  market_id: number | null; product_id: number | null; product_name: string | null; brand: string | null;
  unit_price: Money | null; store_id: number | null; store_name: string | null;
}
export interface ListItem {
  id: number; group_id: number; group_name: string; category_id: number | null; image_url: string | null;
  quantity: Money; preferred_brand: string | null; preferred_product_id: number | null; is_checked: boolean;
  position: number; note: string | null; assigned: AssignedProduct | null;
  added_by_id: number | null; added_by_name: string | null; // ortak listede kalemi ekleyen
}
export interface ShoppingGroup { market_id: number | null; item_ids: number[]; checked_count: number; }
export interface ListSummary {
  id: number; owner_id: number; owner_name: string | null; member_count: number; name: string; icon: string | null; status: "active" | "shopping" | "completed";
  applied_plan: PlanType | null; planned_total: Money | null; item_count: number; checked_count: number;
  created_at: string; updated_at: string; estimated_total: Money | null; top_market_id: number | null;
}
export interface ListDetail extends ListSummary {
  preference_total: Money | null; expected_savings: Money | null; applied_at: string | null;
  completed_at: string | null; items: ListItem[]; shopping_groups: ShoppingGroup[];
  share_code: string | null; members: ListMember[];
}
export interface ListMember { user_id: number; name: string | null; joined_at: string; }

export interface PlanLine {
  item_id: number; group_id: number; group_name: string; quantity: Money; product_id: number;
  product_name: string; brand: string | null; market_id: number; unit_price: Money; store_id: number | null;
  line_total: Money; substituted: boolean; // Tek Market: seçilen marka bu markette yok, başka marka
}
export interface MarketBreakdown { market_id: number; total: Money; item_ids: number[]; }
export interface Plan { plan_type: PlanType; total: Money; lines: PlanLine[]; missing_item_ids: number[]; by_market: MarketBreakdown[]; }
export interface MarketTotal { market_id: number; total: Money; found: number; missing: number; substituted: number; }
export interface OptimizeResult {
  single_market: { available: boolean; warning: string | null; plan: Plan | null; markets: MarketTotal[] };
  combination: Plan; opportunist: Plan;
  savings: { preference_total: Money; opportunist_total: Money; weekly: Money; monthly: Money; yearly: Money };
}

export interface SavingsRecord {
  id: number; list_id: number | null; list_name: string; plan_type: PlanType; preference_total: Money;
  optimized_total: Money; saved_amount: Money; item_count: number; created_at: string;
}
export interface SavingsVault { total_saved: Money; record_count: number; records: SavingsRecord[]; }
export interface CompleteResponse {
  list_id: number; saved_amount: Money; vault_total: Money; note: string | null;
  shopping_savings: Money; // bu alışverişte ortalama fiyatlara göre kazanılan (kutlama ekranı)
}

export interface Store {
  id: number; name: string; market_id: number; market_slug: string; market_name: string;
  latitude: Money | null; longitude: Money | null; distance_km: number | null; selected: boolean;
}

export interface PriceAlert {
  id: number; group_id: number; group_name: string; category_id: number | null; image_url: string | null;
  quantity: Money | null; unit: Unit | null; target_price: Money | null; baseline_price: Money | null;
  current_price: Money | null; current_market_id: number | null; triggered: boolean; triggered_at: string | null;
  unread: boolean; created_at: string;
}
export interface Deal {
  group_id: number; group_name: string; category_id: number | null; image_url: string | null;
  quantity: Money | null; unit: Unit | null; product_id: number; product_name: string; brand: string | null;
  market_id: number; store_id: number | null; price: Money; previous_price: Money; discount_percent: number;
  is_campaign: boolean;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export const num = (v: Money | number | null | undefined): number => (v == null ? 0 : Number(v));

export function getToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}
export function setToken(token: string | null) {
  try { token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY); } catch {}
}

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: (() => void) | null) { onUnauthorized = fn; }

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = "Bearer " + token;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(API_URL + path, {
    method, headers, body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 401 && token) { setToken(null); onUnauthorized?.(); }
  if (!res.ok) {
    let message = "İstek başarısız (" + res.status + ")";
    try {
      const data = await res.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail) && data.detail[0]?.msg) message = data.detail[0].msg;
    } catch {}
    throw new ApiError(res.status, message);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

const qs = (params: Record<string, string | number | undefined | null>) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") s.set(k, String(v));
  const str = s.toString();
  return str ? "?" + str : "";
};

export const api = {
  register: (email: string, password: string, full_name?: string) =>
    request<AuthResponse>("POST", "/auth/register", { email, password, full_name: full_name || null }),
  login: (email: string, password: string) => request<AuthResponse>("POST", "/auth/login", { email, password }),
  me: () => request<User>("GET", "/auth/me"),

  markets: () => request<Market[]>("GET", "/markets"),
  categories: () => request<Category[]>("GET", "/categories"),
  // sort "popular": arama yokken temel ürünler (en çok marka/markette olanlar) önce
  searchProducts: (q: string, categoryId?: number | null, opts: { sort?: "name" | "popular"; limit?: number; subcategoryId?: number | null } = {}) =>
    request<GroupSummary[]>("GET", "/products" + qs({ q, category_id: categoryId, subcategory_id: opts.subcategoryId, limit: opts.limit ?? 100, sort: opts.sort })),
  productGroup: (id: number) => request<GroupDetail>("GET", "/products/" + id),

  lists: () => request<ListSummary[]>("GET", "/lists"),
  list: (id: number) => request<ListDetail>("GET", "/lists/" + id),
  createList: (name: string) => request<ListDetail>("POST", "/lists", { name }),
  deleteList: (id: number) => request<void>("DELETE", "/lists/" + id),
  addItem: (listId: number, groupId: number, preferredProductId?: number | null) =>
    request<ListDetail>("POST", `/lists/${listId}/items`, { group_id: groupId, preferred_product_id: preferredProductId ?? null }),
  updateItem: (
    listId: number, itemId: number,
    patch: Partial<{ quantity: number; is_checked: boolean; preferred_product_id: number | null; preferred_brand: string | null }>,
  ) => request<ListDetail>("PATCH", `/lists/${listId}/items/${itemId}`, patch),
  removeItem: (listId: number, itemId: number) => request<ListDetail>("DELETE", `/lists/${listId}/items/${itemId}`),
  clearPreferences: (listId: number) => request<ListDetail>("POST", `/lists/${listId}/clear-preferences`),
  optimize: (listId: number) => request<OptimizeResult>("GET", `/lists/${listId}/optimize`),
  applyPlan: (listId: number, plan_type: PlanType) => request<ListDetail>("POST", `/lists/${listId}/apply`, { plan_type }),
  cancelPlan: (listId: number) => request<ListDetail>("DELETE", `/lists/${listId}/plan`),
  complete: (listId: number) => request<CompleteResponse>("POST", `/lists/${listId}/complete`),
  // Tamamlanan liste kilitlidir; aynı ürünlerle yeniden açar
  reopenList: (listId: number) => request<ListDetail>("POST", `/lists/${listId}/reopen`),

  shareList: (listId: number) => request<{ share_code: string }>("POST", `/lists/${listId}/share`),
  joinList: (code: string) => request<ListDetail>("POST", "/lists/join", { code }),
  removeMember: (listId: number, userId: number) => request<void>("DELETE", `/lists/${listId}/members/${userId}`),

  savings: () => request<SavingsVault>("GET", "/savings"),

  alerts: () => request<PriceAlert[]>("GET", "/alerts"),
  unreadAlerts: () => request<{ unread: number }>("GET", "/alerts/unread"),
  // productId: seçili ürün (marka/market) takip edilir; boşsa grubun en ucuzu
  createAlert: (groupId: number, targetPrice?: number | null, productId?: number | null) =>
    request<PriceAlert[]>("POST", "/alerts", { group_id: groupId, target_price: targetPrice ?? null, product_id: productId ?? null }),
  deleteAlert: (id: number) => request<void>("DELETE", "/alerts/" + id),
  markAlertsSeen: () => request<void>("POST", "/alerts/seen"),

  deals: () => request<Deal[]>("GET", "/products/deals"),
  findBarcode: (code: string) => request<{ barcode: string; group_id: number }>("GET", "/products/barcode/" + encodeURIComponent(code)),

  nearbyStores: (lat: number, lon: number, distance?: number) =>
    request<Store[]>("GET", "/stores/nearby" + qs({ lat, lon, distance })),
  myStores: () => request<Store[]>("GET", "/me/stores"),
  selectStores: (storeIds: number[]) => request<Store[]>("PUT", "/me/stores", { store_ids: storeIds }),
};

/** "1000 ml" -> "1 L", "500 g" -> "500 g", "15 adet" -> "15'li" */
export function formatSize(quantity: Money | null, unit: Unit | null): string {
  if (quantity == null || unit == null) return "";
  const q = num(quantity);
  const fmt = (n: number) => String(Number(n.toFixed(2))).replace(".", ",");
  if (unit === "ml") return q >= 1000 ? fmt(q / 1000) + " L" : fmt(q) + " ml";
  if (unit === "g") return q >= 1000 ? fmt(q / 1000) + " kg" : fmt(q) + " g";
  return fmt(q) + "'" + countSuffix(q);
}

/** Kilo/litre/adet başına fiyat: (34,50 ₺, 1000 ml) -> "34,50 ₺/L". Miktar bilinmiyorsa null. */
export function unitPrice(price: Money | number | null | undefined, quantity: Money | null, unit: Unit | null) {
  const q = num(quantity);
  if (price == null || !q || !unit) return null;
  const value = unit === "adet" ? num(price) / q : (num(price) / q) * 1000;
  return { value, label: value.toFixed(2).replace(".", ",") + " ₺/" + (unit === "ml" ? "L" : unit === "g" ? "kg" : "adet") };
}

// Türkçe ses uyumu: 15'li, 30'lu, 6'lı, 4'lü
function countSuffix(n: number): string {
  const ones = ["", "li", "li", "lü", "lü", "li", "lı", "li", "li", "lu"];
  const tens = ["", "lu", "li", "lu", "lı", "li", "lı", "li", "li", "lı"];
  n = Math.round(n);
  if (n % 10) return ones[n % 10];
  if (n % 100) return tens[(n % 100) / 10];
  if (n % 1000) return "lü";
  return "li";
}
