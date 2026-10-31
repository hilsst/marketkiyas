/**
 * MarketKıyas sunucusu (FastAPI) istemcisi. Uçlar ve şemalar web arayüzüyle aynıdır
 * (frontend/src/lib/api.ts); burada telefonun kullandıkları tanımlıdır.
 *
 * Adres EXPO_PUBLIC_API_URL ile verilir. Geliştirmede telefon aynı Wi-Fi'deki bilgisayara
 * web arayüzünün /api vekili üzerinden bağlanır (BASLAT.bat: http://<bilgisayar-ip>:3000/api).
 * Bilgisayarın adresi modemden modeme değiştiği için Expo'nun bağlandığı adresten alınır.
 */
import Constants from 'expo-constants';

const devHost = Constants.expoConfig?.hostUri?.split(':')[0] ?? 'localhost';
export const API_URL = process.env.EXPO_PUBLIC_API_URL || `http://${devHost}:3000/api`;

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
  price_history: PricePoint[]; store_prices: { store_id: number; store_name: string; price: Money; updated_at: string | null }[];
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
// Fiyat alarmı: current_price kullanıcının şubelerindeki en ucuz fiyat; triggered = eşiğin altına indi
export interface PriceAlert {
  id: number; group_id: number; group_name: string; category_id: number | null; image_url: string | null;
  quantity: Money | null; unit: Unit | null; target_price: Money | null; baseline_price: Money | null;
  product_id: number | null; product_name: string | null; brand: string | null; // seçili ürün; null = en ucuzu
  current_price: Money | null; current_market_id: number | null; triggered: boolean; triggered_at: string | null;
  unread: boolean; created_at: string;
}
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

// Aktüel: marketlerin haftalık broşür ürünleri. automatic=false olan marketler için yalnızca site bağlantısı var
export interface AktuelSource { slug: string; name: string; url: string; automatic: boolean; item_count: number; updated_at: string | null; }
export interface AktuelItem {
  id: number; market_slug: string; period_key: string; period_label: string; starts_on: string | null; ends_on: string | null;
  upcoming: boolean; title: string; brand: string | null; quantity_text: string | null; details: string | null;
  price: Money; old_price: Money | null; image_url: string | null; source_url: string | null;
}
export interface AktuelResponse { sources: AktuelSource[]; items: AktuelItem[]; }

// Yemek planlayıcı: mutfaklar, tarifler, 1-14 günlük plan ve malzeme maliyeti
export type MealSlot = 'kahvalti' | 'ogle' | 'ara' | 'aksam';
export type CourseType = 'corba' | 'ana' | 'yan' | 'salata' | 'tatli' | 'icecek' | 'ara';
export type Diet = 'vejetaryen' | 'vegan' | 'glutensiz';
export type Allergen = 'gluten' | 'sut' | 'yumurta' | 'kuruyemis' | 'susam' | 'soya' | 'balik' | 'kereviz' | 'hardal';
export type PlanPeriod = 'daily' | 'weekly' | 'custom';
/** 0 = Pazartesi ... 6 = Pazar */
export const WEEKDAY_SHORT = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'];
export const MEAL_SLOT_LABELS: Record<MealSlot, string> = { kahvalti: 'Kahvaltı', ogle: 'Öğle', ara: 'Ara öğün', aksam: 'Akşam' };
export const COURSE_LABELS: Record<CourseType, string> = {
  corba: 'Çorba', ana: 'Ana yemek', yan: 'Yanında', salata: 'Salata', tatli: 'Tatlı', icecek: 'İçecek', ara: 'Ara öğün',
};
export const DIET_LABELS: Record<Diet, string> = { vejetaryen: 'Vejetaryen', vegan: 'Vegan', glutensiz: 'Glutensiz' };
export const ALLERGEN_LABELS: Record<Allergen, string> = {
  gluten: 'Gluten', sut: 'Süt', yumurta: 'Yumurta', kuruyemis: 'Kuruyemiş', susam: 'Susam', soya: 'Soya', balik: 'Balık',
  kereviz: 'Kereviz', hardal: 'Hardal',
};
// Her öğünde önerilen yemek türleri (sunucudaki SLOT_COURSES ile aynı)
export const SLOT_COURSES: Record<MealSlot, CourseType[]> = {
  kahvalti: ['ana', 'icecek'], ogle: ['corba', 'ana', 'yan', 'salata', 'tatli', 'icecek'], ara: ['ara'],
  aksam: ['corba', 'ana', 'yan', 'salata', 'tatli', 'icecek'],
};
/** recipe_count ve examples yalnız malzemesi marketlerde bulunan tariflerden */
export interface Cuisine { slug: string; name: string; icon: string | null; is_default: boolean; recipe_count: number; examples: string[]; }
export interface RecipeSummary {
  id: number; slug: string; name: string; cuisine: string; course: string; course_type: CourseType; pairs_with: string[];
  meal_slots: MealSlot[]; servings: number;
  prep_minutes: number; cook_minutes: number; description: string; icon: string | null; image_url: string | null;
  allergens: Allergen[]; diets: Diet[]; nutrition: Nutrition | null; like_count: number; liked: boolean;
  /** "Dolabımda ne var" aramasında alınması gereken malzemeler */
  missing?: string[] | null;
}
/** "Dolabımda ne var" seçicisi */
export interface IngredientChoice { name: string; recipe_count: number; }
/** Kişi başı yaklaşık değerler */
export interface Nutrition { kcal: number; protein_g: number; carbs_g: number; fat_g: number; }
export interface MealCostLine {
  name: string; needed_quantity: Money; unit: Unit; is_pantry: boolean; recipes: string[];
  match: { group_id: number; name: string; quantity: Money | null; unit: Unit | null; image_url: string | null; price: Money; market_id: number | null } | null;
  packages: number; purchase_cost: Money | null; used_cost: Money | null; approximate: boolean;
}
export interface MealCost {
  purchase_total: Money; used_total: Money; per_serving: Money | null; portions: number; missing_count: number;
  include_pantry: boolean; lines: MealCostLine[]; pantry: string[];
  /** dolabımda var denen, maliyete girmeyenler */ have?: string[];
  /** alınan paketlerden artan kısmın değeri */ leftover_value?: Money;
}
export interface RecipeDetail extends RecipeSummary {
  steps: string[]; ingredients: { name: string; amount_text: string; quantity: Money; unit: Unit; is_pantry: boolean }[]; cost: MealCost;
}
export interface MealPlanSummary {
  id: number; name: string; period: PlanPeriod; cuisine: string; cuisines: string[]; start_date: string; days: number; servings: number;
  meal_slots: MealSlot[]; courses: CourseType[]; diets: Diet[]; avoid_allergens: Allergen[]; entry_count: number;
  weekdays: number[]; budget: Money | null; leftovers: boolean; low_waste: boolean; have: string[];
  exported_list_id: number | null; created_at: string;
}
export interface MealPlanEntry {
  id: number; day_index: number; date: string; slot: MealSlot; course: CourseType; recipe: RecipeSummary;
  /** bu yemek o kaydın kalanı */ leftover_of: number | null; /** bu yemekten kalanlar (iki kat pişir) */ leftover_for: number[];
}
export interface BudgetStatus { budget: Money; total: Money; within: boolean; swaps: number; }
export interface MealPlanDetail extends MealPlanSummary {
  entries: MealPlanEntry[]; cost: MealCost; daily_nutrition: Nutrition | null; budget_status: BudgetStatus | null;
}
export interface MealPlanCreate {
  period: PlanPeriod; cuisines?: string[]; servings: number; meal_slots: MealSlot[]; courses: CourseType[]; start_date?: string | null; name?: string | null;
  diets?: Diet[]; avoid_allergens?: Allergen[];
  days?: number; weekdays?: number[]; budget?: number | null; leftovers?: boolean; low_waste?: boolean; have?: string[];
}
export interface MealPlanExport { list: ListDetail; added: number; skipped: string[]; }

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

/** Fiyatın kaynakta güncellenme zamanı: "bugün 09:15", "dün 18:40", "3 gün önce". */
export function updatedLabel(iso: string | null | undefined, now = new Date()): string | null {
  if (!iso) return null;
  const at = new Date(iso);
  if (isNaN(at.getTime())) return null;
  const day = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((day(now) - day(at)) / 86400000);
  const time = at.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
  if (days <= 0) return 'bugün ' + time;
  if (days === 1) return 'dün ' + time;
  return days + ' gün önce';
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
  // Tamamlanan liste kilitlidir; aynı ürünlerle yeniden açar
  reopenList: (listId: number) => request<ListDetail>('POST', `/lists/${listId}/reopen`),
  // Ortak liste: sahip davet kodu alır, aile üyesi kodla katılır; üye kendini, sahip herkesi çıkarabilir
  shareList: (listId: number) => request<{ share_code: string }>('POST', `/lists/${listId}/share`),
  joinList: (code: string) => request<ListDetail>('POST', '/lists/join', { code }),
  removeMember: (listId: number, userId: number) => request<void>('DELETE', `/lists/${listId}/members/${userId}`),
  productGroup: (id: number) => request<GroupDetail>('GET', '/products/' + id),
  // Muadiller, seçili şubelere göre (şube seçilmemişse boş)
  similarGroups: (id: number) => request<GroupSummary[]>('GET', '/products/' + id + '/similar'),
  deals: () => request<Deal[]>('GET', '/products/deals'),
  aktuel: (market?: string | null) => request<AktuelResponse>('GET', '/aktuel' + qs({ market })),
  myStores: () => request<Store[]>('GET', '/me/stores'),
  alerts: () => request<PriceAlert[]>('GET', '/alerts'),
  createAlert: (groupId: number, targetPrice?: number | null, productId?: number | null) =>
    request<PriceAlert[]>('POST', '/alerts', { group_id: groupId, target_price: targetPrice ?? null, product_id: productId ?? null }),
  deleteAlert: (id: number) => request<void>('DELETE', '/alerts/' + id),
  markAlertsSeen: () => request<void>('POST', '/alerts/seen'),
  family: () => request<MyFamily>('GET', '/family'),
  createFamily: (name: string) => request<MyFamily>('POST', '/family', { name }),
  joinFamily: (code: string) => request<MyFamily>('POST', '/family/join', { code }),
  inviteToFamily: (email: string) => request<MyFamily>('POST', '/family/invites', { email }),
  acceptFamilyInvite: (id: number) => request<MyFamily>('POST', '/family/invites/' + id + '/accept'),
  declineFamilyInvite: (id: number) => request<void>('DELETE', '/family/invites/' + id),
  removeFamilyMember: (userId: number) => request<void>('DELETE', '/family/members/' + userId),
  // Yemek planlayıcı
  cuisines: () => request<Cuisine[]>('GET', '/cuisines'),
  // En sevilenler önce; diyete uymayan / alerjen içeren tarifler gelmez
  ingredients: () => request<IngredientChoice[]>('GET', '/ingredients'),
  pantryRecipes: (have: string[]) =>
    request<RecipeSummary[]>('GET', '/recipes?' + have.map(h => 'have=' + encodeURIComponent(h)).join('&')),
  recipes: (cuisine?: string | null, diets: Diet[] = [], avoid: Allergen[] = []) => {
    const filters = [...diets.map(d => 'diet=' + d), ...avoid.map(a => 'avoid=' + a)].join('&');
    const base = qs({ cuisine });
    return request<RecipeSummary[]>('GET', '/recipes' + base + (filters ? (base ? '&' : '?') + filters : ''));
  },
  likeRecipe: (id: number, like: boolean) => request<void>(like ? 'PUT' : 'DELETE', `/recipes/${id}/like`),
  recipe: (id: number, servings?: number) => request<RecipeDetail>('GET', '/recipes/' + id + qs({ servings })),
  mealPlans: () => request<MealPlanSummary[]>('GET', '/meal-plans'),
  mealPlan: (id: number, includePantry = false) =>
    request<MealPlanDetail>('GET', '/meal-plans/' + id + qs({ include_pantry: includePantry ? 'true' : null })),
  createMealPlan: (body: MealPlanCreate) => request<MealPlanDetail>('POST', '/meal-plans', body),
  updateMealPlan: (id: number, patch: { name?: string; servings?: number }) => request<MealPlanDetail>('PATCH', '/meal-plans/' + id, patch),
  // recipeId boş: "Başka öner"
  changeMealEntry: (planId: number, entryId: number, recipeId?: number | null) =>
    request<MealPlanDetail>('PATCH', `/meal-plans/${planId}/entries/${entryId}`, { recipe_id: recipeId ?? null }),
  // Öğünde istenmeyen yemeği kaldır / kaldırılanı geri ekle (tarif boşsa önerilir)
  removeMealEntry: (planId: number, entryId: number) => request<MealPlanDetail>('DELETE', `/meal-plans/${planId}/entries/${entryId}`),
  addMealEntry: (planId: number, day_index: number, slot: MealSlot, course: CourseType) =>
    request<MealPlanDetail>('POST', `/meal-plans/${planId}/entries`, { day_index, slot, course }),
  deleteMealPlan: (id: number) => request<void>('DELETE', '/meal-plans/' + id),
  exportMealPlan: (id: number, body: { list_id?: number | null; list_name?: string | null; include_pantry?: boolean }) =>
    request<MealPlanExport>('POST', `/meal-plans/${id}/to-list`, body),
};
