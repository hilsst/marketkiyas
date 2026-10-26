// "Son kullanılanlar": listeden çıkarılan ürünler bu cihazda hatırlanır, tek dokunuşla geri eklenir
export interface RecentGroup { group_id: number; name: string; category_id: number | null; }

const KEY = "mk_recent_groups";
const MAX = 16;

export function recentGroups(): RecentGroup[] {
  try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; }
}

export function rememberGroup(g: RecentGroup) {
  try {
    const rest = recentGroups().filter(r => r.group_id !== g.group_id);
    localStorage.setItem(KEY, JSON.stringify([g, ...rest].slice(0, MAX)));
  } catch {}
}
