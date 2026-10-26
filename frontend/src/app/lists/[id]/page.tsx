"use client";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  api, num,
  GroupProduct, ListDetail, ListItem, OptimizeResult, PlanLine, PlanType,
} from "@/lib/api";
import { useGroupIcon, useLists } from "@/lib/store";
import MarketLogo from "@/components/MarketLogo";

type Tab = "items" | "by-market" | "optimize";
type Mode = "single" | "combo" | "cheapest";

const PLAN_OF_MODE: Record<Mode, PlanType> = { single: "single_market", combo: "combination", cheapest: "opportunist" };
const MODE_OF_PLAN: Record<PlanType, Mode> = { single_market: "single", combination: "combo", opportunist: "cheapest" };

const linesByItem = (lines: PlanLine[]) => new Map(lines.map(l => [l.item_id, l]));

export default function ListDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const listId = Number(id);
  const { hydrated, user, marketById, refreshLists, setToast } = useLists();
  const groupIcon = useGroupIcon();
  const [tab, setTab] = useState<Tab>("items");
  const [mode, setMode] = useState<Mode>("single");
  const [detail, setDetail] = useState<ListDetail | null | undefined>(undefined);
  const [opt, setOpt] = useState<OptimizeResult | null>(null);
  const [pickerItemId, setPickerItemId] = useState<number | null>(null);
  const [pickerAlternatives, setPickerAlternatives] = useState<GroupProduct[] | null>(null);
  // Hızlı art arda tıklamalarda yalnızca son isteğin cevabı ekrana yazılır
  const seq = useRef(0);

  const reoptimize = useCallback(() => api.optimize(listId).then(setOpt).catch(() => {}), [listId]);

  useEffect(() => {
    if (!user) return;
    api.list(listId).then(setDetail).catch(() => setDetail(null));
    reoptimize();
  }, [listId, user, reoptimize]);

  const mutate = async (
    call: () => Promise<ListDetail>, opts: { optimistic?: (d: ListDetail) => ListDetail; reopt?: boolean } = {},
  ) => {
    const mine = ++seq.current;
    if (opts.optimistic) setDetail(d => (d ? opts.optimistic!(d) : d));
    try {
      const fresh = await call();
      if (mine === seq.current) setDetail(fresh);
      if (opts.reopt !== false) reoptimize();
      return fresh;
    } catch (e) {
      setToast((e as Error).message);
      if (mine === seq.current) api.list(listId).then(setDetail).catch(() => {});
      return null;
    }
  };

  const updateItem = (itemId: number, patch: Parameters<typeof api.updateItem>[2]) => {
    const onlyCheck = Object.keys(patch).length === 1 && "is_checked" in patch;
    return mutate(() => api.updateItem(listId, itemId, patch), {
      optimistic: onlyCheck
        ? d => ({ ...d, items: d.items.map(i => (i.id === itemId ? { ...i, is_checked: !!patch.is_checked } : i)) })
        : undefined,
      reopt: !onlyCheck,
    });
  };

  const removeItem = async (itemId: number) => {
    const removed = await mutate(() => api.removeItem(listId, itemId), {
      optimistic: d => ({ ...d, items: d.items.filter(i => i.id !== itemId) }),
    });
    if (removed) refreshLists();
  };

  const view = useMemo(() => {
    if (!detail || !opt) return null;
    const itemById = new Map(detail.items.map(i => [i.id, i]));
    const combo = linesByItem(opt.combination.lines);
    const cheap = linesByItem(opt.opportunist.lines);
    const singlePlan = opt.single_market.plan;

    const singleResults = opt.single_market.markets
      .filter(m => m.found > 0)
      .map(m => ({ marketId: m.market_id, total: num(m.total), missing: m.missing, substituted: m.substituted }));
    const bestSingle = singlePlan && singlePlan.by_market[0]
      ? {
          marketId: singlePlan.by_market[0].market_id,
          total: num(singlePlan.total),
          rows: singlePlan.lines.map(line => ({ item: itemById.get(line.item_id)!, line })).filter(r => r.item),
        }
      : null;
    const closestSingle = [...singleResults].sort((a, b) => a.missing - b.missing || a.total - b.total)[0] || null;

    const breakdown = (plan: typeof opt.combination, lines: Map<number, PlanLine>) =>
      plan.by_market
        .map(b => ({
          marketId: b.market_id,
          total: num(b.total),
          rows: b.item_ids.map(iid => ({ item: itemById.get(iid)!, line: lines.get(iid)! })).filter(r => r.item && r.line),
        }))
        .sort((a, b) => b.total - a.total);

    return {
      combo, cheap, singleResults, bestSingle, closestSingle,
      comboTotal: num(opt.combination.total),
      comboBreakdown: breakdown(opt.combination, combo),
      cheapestComboTotal: num(opt.opportunist.total),
      cheapestBreakdown: breakdown(opt.opportunist, cheap),
      savings: num(opt.savings.weekly),
    };
  }, [detail, opt]);

  const shoppingGroups = useMemo(() => {
    if (!detail || !detail.applied_plan) return null;
    const itemById = new Map(detail.items.map(i => [i.id, i]));
    const groups = detail.shopping_groups
      .filter(g => g.market_id != null)
      .map(g => {
        const items = g.item_ids.map(iid => itemById.get(iid)!).filter(Boolean);
        return {
          marketId: g.market_id!,
          items,
          total: items.reduce((s, it) => s + num(it.assigned?.unit_price) * num(it.quantity), 0),
        };
      })
      .sort((a, b) => b.total - a.total);
    const unassigned = detail.shopping_groups.find(g => g.market_id == null)?.item_ids.length || 0;
    return { groups, unassigned };
  }, [detail]);

  const pickerItem = detail?.items.find(i => i.id === pickerItemId);
  const pickerGroupId = pickerItem?.group_id;
  useEffect(() => {
    setPickerAlternatives(null);
    if (pickerGroupId == null) return;
    api.productGroup(pickerGroupId)
      .then(g => setPickerAlternatives(g.products.filter(p => p.price != null).sort((a, b) => num(a.price) - num(b.price))))
      .catch(() => setPickerAlternatives([]));
  }, [pickerGroupId]);

  if (!hydrated || !user || detail === undefined) return <div className="p-6">Yükleniyor…</div>;
  if (!detail) return <div className="p-6 text-center">Liste bulunamadı</div>;

  const list = detail;
  const appliedPlan: Mode | null = list.applied_plan ? MODE_OF_PLAN[list.applied_plan] : null;
  const totalItems = list.items.length;
  const checkedCount = list.items.filter(i => i.is_checked).length;
  const expectedSavings = num(list.expected_savings);

  const handleApplyPlan = async (plan: Mode) => {
    if (plan === "single" && !view?.bestSingle) {
      alert("Tüm ürünler tek bir markette bulunmadığı için bu planı uygulayamazsınız. Lütfen Kombinasyon veya Fırsatçı modunu seçin.");
      return;
    }
    const applied = await mutate(() => api.applyPlan(list.id, PLAN_OF_MODE[plan]), { reopt: false });
    if (applied) {
      setTab("items");
      setToast("Alışveriş planı uygulandı");
      refreshLists();
    }
  };

  const handleDeleteList = async () => {
    if (confirm("Bu listeyi tamamen silmek istediğinize emin misiniz? (Kaydettiğiniz tasarruflar Profil sayfanızda kalıcıdır)")) {
      try {
        await api.deleteList(list.id);
        await refreshLists();
        router.push("/lists");
      } catch (e) { setToast((e as Error).message); }
    }
  };

  const handleFinishShopping = async () => {
    try {
      const done = await api.complete(list.id);
      setToast(num(done.saved_amount) > 0 ? "Tebrikler! Tasarruf kasaya eklendi." : "Alışveriş tamamlandı.");
      setDetail(await api.list(list.id)); // Moddan çık; liste haftaya yeniden kullanılabilir
      reoptimize();
      refreshLists();
    } catch (e) { setToast((e as Error).message); }
  };

  const cancelPlan = () => mutate(() => api.cancelPlan(list.id), { reopt: false });

  const toggle = (item: ListItem) => updateItem(item.id, { is_checked: !item.is_checked });

  return (
    <main className="pb-4">
      <div className="p-4 pb-2">
        <div className="flex justify-between items-start">
          <button onClick={() => router.back()} className="text-gray-600 mb-2">← Geri</button>
          <button onClick={handleDeleteList} className="text-red-500 hover:text-red-700 text-xs font-semibold px-2 py-1 bg-red-50 rounded">
            🗑️ Listeyi Sil
          </button>
        </div>
        <h1 className="text-2xl font-bold">{list.name}</h1>
        <div className="text-xs text-gray-500 mt-1">
          {totalItems} ürün · Tamamlanan: {checkedCount}/{totalItems}
        </div>
        <div className="mt-2 h-1.5 bg-gray-100 rounded-full overflow-hidden">
          <div className="h-full bg-emerald-500 transition-all" style={{ width: (totalItems ? (checkedCount / totalItems) * 100 : 0) + "%" }} />
        </div>
      </div>

      <div className="px-4 mb-3">
        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
          {([["items","Ürünler"],["by-market","Markete Göre"],["optimize","Optimize"]] as [Tab, string][]).map(([t, label]) => (
            <button key={t} onClick={() => setTab(t)}
              className={"flex-1 py-2 rounded-md text-sm font-medium " + (tab === t ? "bg-white shadow text-emerald-700" : "text-gray-600")}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {tab === "items" && (
        <div className="px-4 space-y-3">
          {appliedPlan && shoppingGroups ? (
            <div className="space-y-4">

              {appliedPlan === "cheapest" && expectedSavings > 0 && (
                <div className="bg-gradient-to-br from-emerald-500 to-teal-600 text-white p-4 rounded-xl shadow-md text-center">
                  <div className="text-sm font-medium opacity-90">Fırsatçı Kombinasyon Seçildi!</div>
                  <div className="text-3xl font-black my-1">{expectedSavings.toFixed(2)} ₺ Tasarruf</div>
                  <div className="text-xs bg-black/10 rounded-lg p-2 mt-2 flex justify-around">
                    <div>Haftalık<br/><span className="font-bold">{expectedSavings.toFixed(2)} ₺</span></div>
                    <div>Aylık<br/><span className="font-bold">{(expectedSavings * 4).toFixed(2)} ₺</span></div>
                    <div>Yıllık<br/><span className="font-bold">{(expectedSavings * 52).toFixed(2)} ₺</span></div>
                  </div>
                </div>
              )}

              <div className="bg-emerald-600 text-white p-3 rounded-lg flex justify-between items-center shadow-sm">
                <div className="text-sm font-semibold">
                  🛒 Alışveriş Modu: {appliedPlan === 'cheapest' ? 'Fırsatçı' : appliedPlan === 'combo' ? 'Kombinasyon' : 'Tek Market'}
                </div>
                <button onClick={cancelPlan} className="text-xs bg-emerald-700 hover:bg-emerald-800 px-2 py-1 rounded">
                  İptal Et
                </button>
              </div>

              {shoppingGroups.unassigned > 0 && (
                <div className="text-xs text-orange-600 text-center bg-orange-50 p-3 rounded-lg border border-orange-200">
                  ⚠️ {shoppingGroups.unassigned} ürün {appliedPlan === "single" ? "bu markette" : "seçtiğiniz marketlerde"} bulunamadığı için listede gösterilmiyor.
                </div>
              )}

              {shoppingGroups.groups.map(group => (
                <div key={group.marketId} className="card overflow-hidden border-2 border-emerald-100">
                  <div className="p-3 flex items-center gap-2 bg-emerald-50 border-b border-emerald-100">
                    <MarketLogo id={group.marketId} size={24} />
                    <span className="font-bold text-emerald-900">{marketById(group.marketId)?.name}</span>
                    <span className="text-xs text-emerald-700 ml-auto font-semibold">{group.total.toFixed(2)} ₺</span>
                  </div>
                  <div className="divide-y divide-gray-100">
                    {group.items.map(item => (
                      <div key={item.id}
                        onClick={() => toggle(item)}
                        className={"px-3 py-3 flex items-center gap-3 cursor-pointer transition-all " + (item.is_checked ? "opacity-40 grayscale bg-gray-50" : "hover:bg-gray-50")}>
                        <input type="checkbox" checked={item.is_checked} readOnly
                          className="w-5 h-5 accent-emerald-600 pointer-events-none" />
                        <span className="text-xl">{groupIcon(item.category_id)}</span>
                        <div className="flex-1 min-w-0">
                          <div className={"text-sm font-medium " + (item.is_checked ? "line-through text-gray-500" : "")}>
                            {item.group_name}
                          </div>
                          <div className="text-xs text-gray-500">
                            {item.assigned?.brand || item.assigned?.product_name} × {num(item.quantity)}
                            {item.assigned?.store_name && <span> · {item.assigned.store_name}</span>}
                          </div>
                        </div>
                        <div className={"font-bold " + (item.is_checked ? "text-gray-400" : "text-gray-900")}>
                          {(num(item.assigned?.unit_price) * num(item.quantity)).toFixed(2)} ₺
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}

              {/* Alışverişi Bitir Butonu */}
              <div className="pt-4 border-t border-gray-200 mt-4">
                <button
                  onClick={handleFinishShopping}
                  className="w-full bg-gray-900 hover:bg-black text-white py-4 rounded-xl font-bold shadow-md transition-colors flex justify-center items-center gap-2"
                >
                  ✅ Alışverişi Bitir ve Tasarrufu Kaydet
                </button>
                <p className="text-center text-xs text-gray-500 mt-2">Tasarrufunuz Profil sayfanızda saklanır.</p>
              </div>
            </div>
          ) : (
            <>
              {list.items.map(it => {
                const line = view?.combo.get(it.id);
                const locked = it.preferred_product_id != null || it.preferred_brand != null;
                const qty = num(it.quantity);

                return (
                  <div key={it.id} className={"card p-3 flex flex-col gap-2 transition-all " + (it.is_checked ? "opacity-50 bg-gray-50 grayscale" : "")}>
                    <div className="flex items-center gap-3">
                      <input type="checkbox" checked={it.is_checked}
                        onChange={e => updateItem(it.id, { is_checked: e.target.checked })}
                        className="w-5 h-5 accent-emerald-600" />
                      <span className="text-2xl">{groupIcon(it.category_id)}</span>
                      <div className="flex-1 min-w-0">
                        <div className={"text-sm font-medium " + (it.is_checked ? "line-through text-gray-400" : "")}>
                          {it.group_name}
                        </div>
                        {line && (
                          <div className="text-xs text-gray-500 mt-0.5 flex items-center gap-2">
                            <span className={"px-1.5 py-0.5 rounded " + (locked ? "bg-orange-100 text-orange-700" : "bg-gray-100 text-gray-600")}>
                              {locked ? (line.brand || it.preferred_brand) : "Farketmez (En Ucuz)"}
                            </span>
                            <span>{num(line.unit_price).toFixed(2)} ₺</span>
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        {/* Miktar 1'deyken eksi yerine çöp kutusu: ürünü listeden çıkarır */}
                        {qty > 1 ? (
                          <button onClick={() => updateItem(it.id, { quantity: qty - 1 })} className="w-7 h-7 rounded-full bg-gray-100 text-gray-700">−</button>
                        ) : (
                          <button onClick={() => removeItem(it.id)} aria-label="Listeden çıkar" className="w-7 h-7 rounded-full bg-red-50 text-red-500 text-sm">🗑</button>
                        )}
                        <span className="w-6 text-center text-sm font-semibold">{qty}</span>
                        <button onClick={() => qty < 99 && updateItem(it.id, { quantity: qty + 1 })} className="w-7 h-7 rounded-full bg-gray-100 text-gray-700">+</button>
                      </div>
                    </div>
                    <div className="flex justify-end gap-4">
                      <button onClick={() => removeItem(it.id)} className="text-xs text-red-500 underline font-medium">
                        Listeden Çıkar
                      </button>
                      <button onClick={() => setPickerItemId(it.id)} className="text-xs text-emerald-600 underline font-medium">
                        Marka Değiştir
                      </button>
                    </div>
                  </div>
                );
              })}
              <button onClick={() => router.push("/")} className="w-full border-2 border-dashed border-gray-300 rounded-xl py-3 text-gray-500 text-sm">
                + Ürün ekle
              </button>
            </>
          )}
        </div>
      )}

      {tab === "by-market" && view && (
        <div className="px-4 space-y-3">
          <div className="card p-4 bg-emerald-50 border-emerald-200">
            <div className="text-xs text-emerald-700 font-semibold">SEÇTİĞİNİZ MARKALARLA TOPLAM</div>
            <div className="text-2xl font-bold text-emerald-800 mt-1">{view.comboTotal.toFixed(2)} ₺</div>
            <div className="text-xs text-emerald-700 mt-0.5">{view.comboBreakdown.length} markette</div>
          </div>
          {view.comboBreakdown.map(({ marketId, total, rows }) => (
            <div key={marketId} className="card overflow-hidden">
              <div className="p-3 flex items-center gap-2 border-b border-gray-100 bg-gray-50">
                <MarketLogo id={marketId} size={28} />
                <span className="font-semibold">{marketById(marketId)?.name}</span>
                <span className="text-xs text-gray-500">· {rows.length} ürün</span>
                <span className="ml-auto font-bold text-gray-800">{total.toFixed(2)} ₺</span>
              </div>
              <div className="divide-y divide-gray-50">
                {rows.map(({ item, line }) => {
                  const cheapest = view.cheap.get(item.id);
                  const diff = cheapest ? num(line.unit_price) - num(cheapest.unit_price) : 0;

                  return (
                    <div key={item.id} className={"px-3 py-2 flex items-center gap-2 transition-all " + (item.is_checked ? "opacity-40 line-through bg-gray-50" : "")}>
                      <span className="text-lg">{groupIcon(item.category_id)}</span>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm truncate">{item.group_name}</div>
                        <div className="text-xs text-gray-500">{line.brand || line.product_name} × {num(item.quantity)}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-semibold">{num(line.line_total).toFixed(2)} ₺</div>
                        {diff > 0 && !item.is_checked && (
                          <div className="text-[10px] text-orange-600 font-medium">
                            +{diff.toFixed(2)} ₺ fark
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {(tab === "by-market" || tab === "optimize") && !view && (
        <div className="px-4 text-center text-gray-400 py-8">Hesaplanıyor…</div>
      )}

      {tab === "optimize" && view && (
        <div className="px-4 space-y-3">
          <div className="flex gap-2">
            {([["single","Tek Market"],["combo","Kombinasyon"],["cheapest","Fırsatçı 🚀"]] as [Mode, string][]).map(([m, l]) => (
              <button key={m} onClick={() => setMode(m)}
                className={"flex-1 py-2 rounded-lg text-xs font-medium border " + (mode === m ? "bg-emerald-600 text-white border-emerald-600" : "bg-white text-gray-700 border-gray-200")}>
                {l}
              </button>
            ))}
          </div>

          <div className="card p-4">
            {mode === "cheapest" && view.savings > 0 && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 mb-4 text-center shadow-sm">
                <div className="text-emerald-800 font-black text-xl">{view.savings.toFixed(2)} ₺ Tasarruf Ettiniz!</div>
                <div className="text-xs text-emerald-700 flex justify-around mt-3 font-semibold bg-white/70 py-2 rounded-lg border border-emerald-100">
                  <div className="flex flex-col">
                    <span className="text-[10px] uppercase opacity-70">Haftalık</span>
                    <span>{view.savings.toFixed(2)} ₺</span>
                  </div>
                  <div className="flex flex-col border-x border-emerald-100 px-4">
                    <span className="text-[10px] uppercase opacity-70">Aylık</span>
                    <span>{(view.savings * 4).toFixed(2)} ₺</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] uppercase opacity-70">Yıllık</span>
                    <span>{(view.savings * 52).toFixed(2)} ₺</span>
                  </div>
                </div>
              </div>
            )}

            <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-100">
              <div>
                <div className="text-xs text-gray-500">
                  {mode === "single" ? "Sizin Seçimlerinizle (Tek Market)" :
                   mode === "combo" ? "Sizin Seçimlerinizle (Kombinasyon)" :
                   "Tüm Ürünlerin En Ucuzu (Fırsatçı)"}
                </div>
                <div className={"text-2xl font-bold " + (mode === "cheapest" ? "text-emerald-700" : "text-gray-800")}>
                  {mode === "single" ? (view.bestSingle ? view.bestSingle.total.toFixed(2) : "-") :
                   mode === "combo" ? view.comboTotal.toFixed(2) :
                   view.cheapestComboTotal.toFixed(2)} ₺
                </div>
                <div className="text-xs text-gray-500">
                  {mode === "single" ? (view.bestSingle ? marketById(view.bestSingle.marketId)?.name : "Eksiksiz Market Yok") :
                   mode === "combo" ? view.comboBreakdown.length + " market" :
                   view.cheapestBreakdown.length + " market"}
                </div>
              </div>
            </div>

            {mode === "single" && (
              <div className="space-y-2 mb-4">
                {view.bestSingle ? (
                  <div className="bg-emerald-50 p-3 rounded-lg border border-emerald-100 mb-3">
                    <div className="text-sm text-emerald-800 font-bold mb-1">✅ Tüm ürünler tek markette bulundu!</div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <MarketLogo id={view.bestSingle.marketId} size={28} />
                        <span className="font-bold text-lg">{marketById(view.bestSingle.marketId)?.name}</span>
                      </div>
                      <span className="font-bold text-emerald-700 text-xl">{view.bestSingle.total.toFixed(2)} ₺</span>
                    </div>
                    <div className="mt-2 divide-y divide-emerald-100 text-sm">
                      {view.bestSingle.rows.map(({ item, line }) => (
                        <div key={item.id} className="py-1.5 flex justify-between gap-2">
                          <div className="min-w-0">
                            {item.group_name} <span className="text-gray-500 text-xs">({line.substituted ? line.product_name : line.brand || line.product_name})</span>
                            {line.substituted && (
                              <div className="text-[11px] text-orange-600">
                                Seçtiğiniz {item.preferred_brand ? "\"" + item.preferred_brand + "\" markası" : "ürün"} burada yok, benzeri alındı
                              </div>
                            )}
                          </div>
                          <span className="text-gray-700 shrink-0">{num(line.line_total).toFixed(2)} ₺</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="bg-orange-50 p-3 rounded-lg border border-orange-200 mb-3">
                    <div className="text-sm text-orange-800 font-bold mb-1">⚠️ Hiçbir market listedeki tüm ürünleri satmıyor.</div>
                    {view.closestSingle && (
                      <div className="text-xs text-orange-700 leading-tight">
                        En yakın market: <b>{marketById(view.closestSingle.marketId)?.name}</b> ({view.closestSingle.missing} ürün hiçbir markayla yok).<br/>
                        Diğer ürünler için Kombinasyon veya Fırsatçı modunu kullanın.
                      </div>
                    )}
                  </div>
                )}

                <div className="text-sm font-semibold text-gray-700">Market Bazlı Toplamlar</div>
                {view.singleResults.map(r => (
                  <div key={r.marketId} className="flex justify-between text-sm py-1">
                    <span className="text-gray-600">{marketById(r.marketId)?.name}</span>
                    <span>
                      {r.total.toFixed(2)} ₺
                      {r.substituted > 0 && <span className="text-xs text-orange-600 font-medium"> ({r.substituted} farklı marka)</span>}
                      {r.missing > 0 && <span className="text-xs text-red-500 font-medium"> ({r.missing} ürün yok)</span>}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {mode === "combo" && (
              <div className="space-y-2 mb-4">
                <div className="text-sm font-semibold text-gray-700 mb-2">Kombinasyon Dağılımı (Seçimlerinizle)</div>
                {view.comboBreakdown.map(({ marketId, total }) => (
                  <div key={marketId} className="flex items-center justify-between text-sm py-1">
                    <div className="flex items-center gap-2">
                      <MarketLogo id={marketId} size={20} />
                      <span>{marketById(marketId)?.name}</span>
                    </div>
                    <span className="font-semibold">{total.toFixed(2)} ₺</span>
                  </div>
                ))}
              </div>
            )}

            {mode === "cheapest" && (
              <div className="space-y-4 mb-4">
                <div className="text-sm font-semibold text-gray-700">Market Dağılımı (Fırsatçı)</div>
                {view.cheapestBreakdown.map(({ marketId, total, rows }) => (
                  <div key={marketId} className="border border-gray-100 rounded-lg overflow-hidden shadow-sm">
                    <div className="bg-emerald-50/50 p-2.5 flex justify-between font-medium text-sm border-b border-gray-100">
                      <div className="flex items-center gap-2">
                        <MarketLogo id={marketId} size={20} />
                        <span>{marketById(marketId)?.name}</span>
                      </div>
                      <span className="font-bold">{total.toFixed(2)} ₺</span>
                    </div>
                    <div className="divide-y divide-gray-50 bg-white">
                      {rows.map(({ item, line }) => (
                        <div key={item.id} className={"px-3 py-2 flex justify-between text-sm items-center " + (item.is_checked ? "opacity-40 line-through" : "")}>
                          <div>
                            <span className="mr-2">{groupIcon(item.category_id)}</span>
                            {item.group_name} <span className="text-gray-500 text-xs">({line.brand || line.product_name})</span>
                          </div>
                          <div className="text-gray-600 font-medium">{num(line.line_total).toFixed(2)} ₺</div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-2 pt-4 border-t border-gray-100">
               <button
                  onClick={() => handleApplyPlan(mode)}
                  className={"w-full py-3 rounded-xl font-bold shadow-sm transition-colors flex items-center justify-center gap-2 " +
                    (mode === "single" && !view.bestSingle ? "bg-gray-300 text-gray-500 cursor-not-allowed" : "bg-emerald-600 hover:bg-emerald-700 text-white")}
                >
                  <span>🛒</span> Bu Planı Alışveriş Listeme Uygula
                </button>
            </div>

            {mode === "combo" && view.savings > 0 && (
              <button
                // Yalnızca Fırsatçı sekmesine geçer; marka seçimleri silinmez, Tek Market/Kombinasyon'a dönülebilir
                onClick={() => setMode("cheapest")}
                className="mt-4 p-3 bg-orange-50 hover:bg-orange-100 transition-colors rounded-lg border border-orange-200 flex items-start gap-2 text-left w-full cursor-pointer group"
              >
                <span className="text-xl group-hover:scale-110 transition-transform">💡</span>
                <div className="text-xs text-orange-800 leading-tight">
                  Seçtiğiniz markalar yerine <b>MARKA FARKETMEZ</b> derseniz, tüm ürünlerin en ucuzunu alarak <b>{view.savings.toFixed(2)} ₺</b> daha az ödeyebilirsiniz. <u className="font-semibold ml-1">Fırsatçı planını görmek için tıklayın.</u>
                </div>
              </button>
            )}
          </div>
        </div>
      )}

      {pickerItem && (
        <div className="fixed inset-0 bg-black/40 flex items-end z-50" onClick={() => setPickerItemId(null)}>
          <div className="bg-white w-full max-w-md mx-auto rounded-t-2xl p-4 max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <div>
                <div className="text-lg font-bold">{pickerItem.group_name}</div>
                <div className="text-xs text-gray-500">Tercih ettiğiniz markayı seçin</div>
              </div>
              <button onClick={() => setPickerItemId(null)} className="text-gray-400 text-2xl">&times;</button>
            </div>

            <div className="space-y-2">
              <button onClick={() => { updateItem(pickerItem.id, { preferred_product_id: null }); setPickerItemId(null); }}
                className={"w-full text-left p-3 rounded-lg border " + (pickerItem.preferred_product_id == null && pickerItem.preferred_brand == null ? "border-emerald-500 bg-emerald-50" : "border-gray-200")}>
                <div className="font-semibold text-emerald-700">Farketmez (En Ucuzu Al)</div>
                <div className="text-xs text-gray-500">Otomatik olarak en uygun fiyatlı markayı seçer.</div>
              </button>

              {pickerAlternatives === null && <div className="text-center text-sm text-gray-400 py-3">Yükleniyor…</div>}
              {pickerAlternatives?.map(p => (
                <button key={p.id} onClick={() => { updateItem(pickerItem.id, { preferred_product_id: p.id }); setPickerItemId(null); }}
                  className={"w-full text-left p-3 rounded-lg border flex items-center justify-between " + (pickerItem.preferred_product_id === p.id ? "border-emerald-500 bg-emerald-50" : "border-gray-200")}>
                  <div>
                    <div className="font-semibold flex items-center gap-2">
                       <MarketLogo id={p.market_id} size={18} /> {p.brand || p.name}
                    </div>
                    <div className="text-xs text-gray-500">{marketById(p.market_id)?.name}</div>
                  </div>
                  <div className="font-bold text-gray-800">{num(p.price).toFixed(2)} ₺</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

    </main>
  );
}
