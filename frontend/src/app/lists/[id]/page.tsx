"use client";
import { useParams, useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useLists } from "@/lib/store";
import { GROUPS, PRODUCTS, MARKETS, MARKET_MAP } from "@/lib/demo-data";
import MarketLogo from "@/components/MarketLogo";

function getPrices(groupId, preferredProductId) {
  const prods = PRODUCTS.filter(p => p.groupId === groupId && p.inStock);
  if (preferredProductId) {
    const p = prods.find(x => x.id === preferredProductId);
    if (p) return { [p.market]: { price: p.price, brand: p.brand, isPromo: p.isPromo, prodId: p.id } };
  }
  const map = {};
  for (const p of prods) {
    if (!map[p.market] || p.price < map[p.market].price) {
      map[p.market] = { price: p.price, brand: p.brand, isPromo: p.isPromo, prodId: p.id };
    }
  }
  return map;
}

function getCheapestPrices(groupId) {
  return getPrices(groupId, null);
}

function assignMarkets(list, ignorePrefs = false) {
  return list.items.map(it => {
    const prices = ignorePrefs ? getCheapestPrices(it.groupId) : getPrices(it.groupId, it.preferredProductId);
    const allowed = it.preferredMarket && !ignorePrefs ? [it.preferredMarket] : Object.keys(prices);
    const candidates = allowed.filter(m => prices[m]);
    if (!candidates.length) return { item: it, market: null, info: null };
    const best = candidates.reduce((a, b) => prices[a].price <= prices[b].price ? a : b);
    return { item: it, market: best, info: prices[best] };
  });
}

export default function ListDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const listId = Number(id);
  const { lists, updateItem, deleteList, clearPreferences, addSavings, hydrated, setToast } = useLists();
  const [tab, setTab] = useState("items");
  const [mode, setMode] = useState("single"); 
  
  const [appliedPlan, setAppliedPlan] = useState(null); 
  const [pickerItemId, setPickerItemId] = useState(null);

  const list = lists.find(l => l.id === listId);

  const byMarket = useMemo(() => {
    if (!list) return null;
    const assignments = assignMarkets(list, false);
    const grouped = {};
    let grand = 0;
    for (const a of assignments) {
      if (!a.market || !a.info) continue;
      (grouped[a.market] = grouped[a.market] || []).push({ item: a.item, info: a.info });
      grand += a.info.price * a.item.quantity;
    }
    return { grouped, grand };
  }, [list]);

  const optimize = useMemo(() => {
    if (!list) return null;
    const assignmentsPrefs = assignMarkets(list, false).filter(a => a.market);
    const assignmentsCheap = assignMarkets(list, true).filter(a => a.market);

    const singleResults = MARKETS.map(m => {
      let total = 0, covered = 0;
      for (const a of assignmentsPrefs) {
        const prices = getPrices(a.item.groupId, a.item.preferredProductId);
        if (prices[m.slug]) { total += prices[m.slug].price * a.item.quantity; covered++; }
      }
      return { slug: m.slug, name: m.name, total, covered, missing: assignmentsPrefs.length - covered };
    }).filter(r => r.covered > 0);
    
    const fullSingles = singleResults.filter(r => r.missing === 0);
    const bestSingle = fullSingles.length > 0 ? [...fullSingles].sort((a, b) => a.total - b.total)[0] : null;
    const closestSingle = singleResults.length > 0 ? [...singleResults].sort((a, b) => a.missing - b.missing || a.total - b.total)[0] : null;

    let comboTotal = 0;
    const comboBreakdown = {};
    for (const a of assignmentsPrefs) {
      comboTotal += a.info.price * a.item.quantity;
      const e = comboBreakdown[a.market] = comboBreakdown[a.market] || { count: 0, total: 0 };
      e.count++; e.total += a.info.price * a.item.quantity;
    }

    let cheapestComboTotal = 0;
    const cheapestBreakdown = {};
    for (const a of assignmentsCheap) {
      cheapestComboTotal += a.info.price * a.item.quantity;
      const e = cheapestBreakdown[a.market] = cheapestBreakdown[a.market] || { items: [], total: 0 };
      e.items.push(a);
      e.total += a.info.price * a.item.quantity;
    }

    const savings = Math.max(0, comboTotal - cheapestComboTotal);

    return { singleResults, bestSingle, closestSingle, comboTotal, comboBreakdown, cheapestComboTotal, cheapestBreakdown, savings };
  }, [list]);

  const shoppingGroups = useMemo(() => {
    if (!list || !appliedPlan) return null;
    
    let itemsToProcess = [];
    if (appliedPlan === "cheapest") {
      itemsToProcess = assignMarkets(list, true).filter(a => a.market);
    } else if (appliedPlan === "combo") {
      itemsToProcess = assignMarkets(list, false).filter(a => a.market);
    } else if (appliedPlan === "single" && optimize?.bestSingle) {
      itemsToProcess = assignMarkets(list, false).filter(a => a.market === optimize.bestSingle.slug);
    }

    const grouped = {};
    itemsToProcess.forEach(a => {
      (grouped[a.market] = grouped[a.market] || []).push(a);
    });

    return Object.entries(grouped).map(([slug, items]) => ({
      slug,
      items,
      total: items.reduce((s, x) => s + x.info.price * x.item.quantity, 0)
    })).sort((a, b) => b.total - a.total);

  }, [list, appliedPlan, optimize]);

  if (!hydrated) return <div className="p-6">Yükleniyor…</div>;
  if (!list) return <div className="p-6 text-center">Liste bulunamadı</div>;

  const totalItems = list.items.length;
  const checkedCount = list.items.filter(i => i.isChecked).length;
  const pickerItem = list.items.find(i => i.id === pickerItemId);
  const pickerGroup = pickerItem ? GROUPS.find(x => x.id === pickerItem.groupId) : null;
  const pickerAlternatives = pickerGroup ? PRODUCTS.filter(p => p.groupId === pickerGroup.id && p.inStock).sort((a,b) => a.price - b.price) : [];

  const handleApplyPlan = (plan) => {
    if (plan === "single" && !optimize.bestSingle) {
      alert("Tüm ürünler tek bir markette bulunmadığı için bu planı uygulayamazsınız. Lütfen Kombinasyon veya Fırsatçı modunu seçin.");
      return;
    }
    setAppliedPlan(plan);
    setTab("items");
    setToast("Alışveriş planı uygulandı");
  };

  const handleDeleteList = () => {
    if (confirm("Bu listeyi tamamen silmek istediğinize emin misiniz? (Kaydettiğiniz tasarruflar Profil sayfanızda kalıcıdır)")) {
      deleteList(list.id);
      router.push("/lists");
    }
  };

  const handleFinishShopping = () => {
    if (appliedPlan === "cheapest" && optimize.savings > 0) {
      addSavings({
        date: new Date().toISOString(),
        amount: optimize.savings,
        listName: list.name,
        itemCount: list.items.length
      });
      setToast("Tebrikler! Tasarruf kasaya eklendi.");
    } else {
      setToast("Alışveriş tamamlandı.");
    }
    setAppliedPlan(null); // Moddan çık
  };

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
          {[["items","Ürünler"],["by-market","Markete Göre"],["optimize","Optimize"]].map(([t, label]) => (
            <button key={t} onClick={() => setTab(t)}
              className={"flex-1 py-2 rounded-md text-sm font-medium " + (tab === t ? "bg-white shadow text-emerald-700" : "text-gray-600")}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {tab === "items" && (
        <div className="px-4 space-y-3">
          {appliedPlan ? (
            <div className="space-y-4">
              
              {appliedPlan === "cheapest" && optimize.savings > 0 && (
                <div className="bg-gradient-to-br from-emerald-500 to-teal-600 text-white p-4 rounded-xl shadow-md text-center">
                  <div className="text-sm font-medium opacity-90">Fırsatçı Kombinasyon Seçildi!</div>
                  <div className="text-3xl font-black my-1">{optimize.savings.toFixed(2)} ₺ Tasarruf</div>
                  <div className="text-xs bg-black/10 rounded-lg p-2 mt-2 flex justify-around">
                    <div>Haftalık<br/><span className="font-bold">{optimize.savings.toFixed(2)} ₺</span></div>
                    <div>Aylık<br/><span className="font-bold">{(optimize.savings * 4).toFixed(2)} ₺</span></div>
                    <div>Yıllık<br/><span className="font-bold">{(optimize.savings * 52).toFixed(2)} ₺</span></div>
                  </div>
                </div>
              )}

              <div className="bg-emerald-600 text-white p-3 rounded-lg flex justify-between items-center shadow-sm">
                <div className="text-sm font-semibold">
                  🛒 Alışveriş Modu: {appliedPlan === 'cheapest' ? 'Fırsatçı' : appliedPlan === 'combo' ? 'Kombinasyon' : 'Tek Market'}
                </div>
                <button onClick={() => setAppliedPlan(null)} className="text-xs bg-emerald-700 hover:bg-emerald-800 px-2 py-1 rounded">
                  İptal Et
                </button>
              </div>

              {appliedPlan === "single" && optimize.bestSingle && list.items.length > optimize.bestSingle.covered && (
                <div className="text-xs text-orange-600 text-center bg-orange-50 p-3 rounded-lg border border-orange-200">
                  ⚠️ {list.items.length - optimize.bestSingle.covered} ürün bu markette bulunamadığı için listede gösterilmiyor.
                </div>
              )}

              {shoppingGroups.map(group => (
                <div key={group.slug} className="card overflow-hidden border-2 border-emerald-100">
                  <div className="p-3 flex items-center gap-2 bg-emerald-50 border-b border-emerald-100">
                    <MarketLogo slug={group.slug} size={24} />
                    <span className="font-bold text-emerald-900">{MARKET_MAP[group.slug].name}</span>
                    <span className="text-xs text-emerald-700 ml-auto font-semibold">{group.total.toFixed(2)} ₺</span>
                  </div>
                  <div className="divide-y divide-gray-100">
                    {group.items.map(({ item, info }) => {
                      const g = GROUPS.find(x => x.id === item.groupId);
                      return (
                        <div key={item.id} 
                          onClick={() => updateItem(list.id, item.id, { isChecked: !item.isChecked })}
                          className={"px-3 py-3 flex items-center gap-3 cursor-pointer transition-all " + (item.isChecked ? "opacity-40 grayscale bg-gray-50" : "hover:bg-gray-50")}>
                          <input type="checkbox" checked={item.isChecked} readOnly
                            className="w-5 h-5 accent-emerald-600 pointer-events-none" />
                          <span className="text-xl">{g.emoji}</span>
                          <div className="flex-1 min-w-0">
                            <div className={"text-sm font-medium " + (item.isChecked ? "line-through text-gray-500" : "")}>
                              {g.name}
                            </div>
                            <div className="text-xs text-gray-500">{info.brand} × {item.quantity}</div>
                          </div>
                          <div className={"font-bold " + (item.isChecked ? "text-gray-400" : "text-gray-900")}>
                            {(info.price * item.quantity).toFixed(2)} ₺
                          </div>
                        </div>
                      )
                    })}
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
                const g = GROUPS.find(x => x.id === it.groupId);
                if (!g) return null;
                const prices = getPrices(it.groupId, it.preferredProductId);
                const cheapest = Object.entries(prices).sort((a, b) => a[1].price - b[1].price)[0];
                
                return (
                  <div key={it.id} className={"card p-3 flex flex-col gap-2 transition-all " + (it.isChecked ? "opacity-50 bg-gray-50 grayscale" : "")}>
                    <div className="flex items-center gap-3">
                      <input type="checkbox" checked={it.isChecked}
                        onChange={e => updateItem(list.id, it.id, { isChecked: e.target.checked })}
                        className="w-5 h-5 accent-emerald-600" />
                      <span className="text-2xl">{g.emoji}</span>
                      <div className="flex-1 min-w-0">
                        <div className={"text-sm font-medium " + (it.isChecked ? "line-through text-gray-400" : "")}>
                          {g.name}
                        </div>
                        {cheapest && (
                          <div className="text-xs text-gray-500 mt-0.5 flex items-center gap-2">
                            <span className={"px-1.5 py-0.5 rounded " + (it.preferredProductId ? "bg-orange-100 text-orange-700" : "bg-gray-100 text-gray-600")}>
                              {it.preferredProductId ? cheapest[1].brand : "Farketmez (En Ucuz)"}
                            </span>
                            <span>{cheapest[1].price.toFixed(2)} ₺</span>
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <button onClick={() => updateItem(list.id, it.id, { quantity: Math.max(1, it.quantity - 1) })} className="w-7 h-7 rounded-full bg-gray-100 text-gray-700">−</button>
                        <span className="w-6 text-center text-sm font-semibold">{it.quantity}</span>
                        <button onClick={() => updateItem(list.id, it.id, { quantity: Math.min(99, it.quantity + 1) })} className="w-7 h-7 rounded-full bg-gray-100 text-gray-700">+</button>
                      </div>
                    </div>
                    <div className="flex justify-end">
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

      {tab === "by-market" && byMarket && (
        <div className="px-4 space-y-3">
          <div className="card p-4 bg-emerald-50 border-emerald-200">
            <div className="text-xs text-emerald-700 font-semibold">SEÇTİĞİNİZ MARKALARLA TOPLAM</div>
            <div className="text-2xl font-bold text-emerald-800 mt-1">{byMarket.grand.toFixed(2)} ₺</div>
            <div className="text-xs text-emerald-700 mt-0.5">{Object.keys(byMarket.grouped).length} markette</div>
          </div>
          {Object.entries(byMarket.grouped).sort((a, b) => {
              const tot = (arr) => arr.reduce((s, x) => s + x.info.price * x.item.quantity, 0);
              return tot(b[1]) - tot(a[1]);
            }).map(([slug, items]) => {
              const total = items.reduce((s, x) => s + x.info.price * x.item.quantity, 0);
              return (
                <div key={slug} className="card overflow-hidden">
                  <div className="p-3 flex items-center gap-2 border-b border-gray-100 bg-gray-50">
                    <MarketLogo slug={slug} size={28} />
                    <span className="font-semibold">{MARKET_MAP[slug].name}</span>
                    <span className="text-xs text-gray-500">· {items.length} ürün</span>
                    <span className="ml-auto font-bold text-gray-800">{total.toFixed(2)} ₺</span>
                  </div>
                  <div className="divide-y divide-gray-50">
                    {items.map(({ item, info }) => {
                      const g = GROUPS.find(x => x.id === item.groupId);
                      const cheapestAvail = Object.values(getCheapestPrices(item.groupId)).sort((a,b)=>a.price-b.price)[0];
                      const diff = cheapestAvail && info.price > cheapestAvail.price ? info.price - cheapestAvail.price : 0;

                      return (
                        <div key={item.id} className={"px-3 py-2 flex items-center gap-2 transition-all " + (item.isChecked ? "opacity-40 line-through bg-gray-50" : "")}>
                          <span className="text-lg">{g.emoji}</span>
                          <div className="flex-1 min-w-0">
                            <div className="text-sm truncate">{g.name}</div>
                            <div className="text-xs text-gray-500">{info.brand} × {item.quantity}</div>
                          </div>
                          <div className="text-right">
                            <div className="text-sm font-semibold">{(info.price * item.quantity).toFixed(2)} ₺</div>
                            {diff > 0 && !item.isChecked && (
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
              );
            })}
        </div>
      )}

      {tab === "optimize" && optimize && (
        <div className="px-4 space-y-3">
          <div className="flex gap-2">
            {[["single","Tek Market"],["combo","Kombinasyon"],["cheapest","Fırsatçı 🚀"]].map(([m, l]) => (
              <button key={m} onClick={() => setMode(m)}
                className={"flex-1 py-2 rounded-lg text-xs font-medium border " + (mode === m ? "bg-emerald-600 text-white border-emerald-600" : "bg-white text-gray-700 border-gray-200")}>
                {l}
              </button>
            ))}
          </div>

          <div className="card p-4">
            {mode === "cheapest" && optimize.savings > 0 && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 mb-4 text-center shadow-sm">
                <div className="text-emerald-800 font-black text-xl">{optimize.savings.toFixed(2)} ₺ Tasarruf Ettiniz!</div>
                <div className="text-xs text-emerald-700 flex justify-around mt-3 font-semibold bg-white/70 py-2 rounded-lg border border-emerald-100">
                  <div className="flex flex-col">
                    <span className="text-[10px] uppercase opacity-70">Haftalık</span>
                    <span>{optimize.savings.toFixed(2)} ₺</span>
                  </div>
                  <div className="flex flex-col border-x border-emerald-100 px-4">
                    <span className="text-[10px] uppercase opacity-70">Aylık</span>
                    <span>{(optimize.savings * 4).toFixed(2)} ₺</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] uppercase opacity-70">Yıllık</span>
                    <span>{(optimize.savings * 52).toFixed(2)} ₺</span>
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
                  {mode === "single" ? (optimize.bestSingle ? optimize.bestSingle.total.toFixed(2) : "-") : 
                   mode === "combo" ? optimize.comboTotal.toFixed(2) : 
                   optimize.cheapestComboTotal.toFixed(2)} ₺
                </div>
                <div className="text-xs text-gray-500">
                  {mode === "single" ? (optimize.bestSingle ? optimize.bestSingle.name : "Eksiksiz Market Yok") : 
                   mode === "combo" ? Object.keys(optimize.comboBreakdown).length + " market" : 
                   Object.keys(optimize.cheapestBreakdown).length + " market"}
                </div>
              </div>
            </div>

            {mode === "single" && (
              <div className="space-y-2 mb-4">
                {optimize.bestSingle ? (
                  <div className="bg-emerald-50 p-3 rounded-lg border border-emerald-100 mb-3">
                    <div className="text-sm text-emerald-800 font-bold mb-1">✅ Tüm ürünler tek markette bulundu!</div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <MarketLogo slug={optimize.bestSingle.slug} size={28} />
                        <span className="font-bold text-lg">{optimize.bestSingle.name}</span>
                      </div>
                      <span className="font-bold text-emerald-700 text-xl">{optimize.bestSingle.total.toFixed(2)} ₺</span>
                    </div>
                  </div>
                ) : (
                  <div className="bg-orange-50 p-3 rounded-lg border border-orange-200 mb-3">
                    <div className="text-sm text-orange-800 font-bold mb-1">⚠️ Hiçbir market tüm ürünleri eksiksiz bulundurmuyor.</div>
                    {optimize.closestSingle && (
                      <div className="text-xs text-orange-700 leading-tight">
                        En yakın market: <b>{optimize.closestSingle.name}</b> ({optimize.closestSingle.missing} ürün eksik).<br/> 
                        Diğer ürünler için Kombinasyon veya Fırsatçı modunu kullanın.
                      </div>
                    )}
                  </div>
                )}

                <div className="text-sm font-semibold text-gray-700">Market Bazlı Toplamlar</div>
                {optimize.singleResults.map(r => (
                  <div key={r.slug} className="flex justify-between text-sm py-1">
                    <span className="text-gray-600">{r.name}</span>
                    <span>{r.total.toFixed(2)} ₺ {r.missing > 0 && <span className="text-xs text-red-500 font-medium">({r.missing} eksik)</span>}</span>
                  </div>
                ))}
              </div>
            )}

            {mode === "combo" && (
              <div className="space-y-2 mb-4">
                <div className="text-sm font-semibold text-gray-700 mb-2">Kombinasyon Dağılımı (Seçimlerinizle)</div>
                {Object.entries(optimize.comboBreakdown).map(([slug, v]) => (
                  <div key={slug} className="flex items-center justify-between text-sm py-1">
                    <div className="flex items-center gap-2">
                      <MarketLogo slug={slug} size={20} />
                      <span>{MARKET_MAP[slug].name}</span>
                    </div>
                    <span className="font-semibold">{v.total.toFixed(2)} ₺</span>
                  </div>
                ))}
              </div>
            )}

            {mode === "cheapest" && (
              <div className="space-y-4 mb-4">
                <div className="text-sm font-semibold text-gray-700">Market Dağılımı (Fırsatçı)</div>
                {Object.entries(optimize.cheapestBreakdown).sort((a,b)=>b[1].total - a[1].total).map(([slug, data]) => (
                  <div key={slug} className="border border-gray-100 rounded-lg overflow-hidden shadow-sm">
                    <div className="bg-emerald-50/50 p-2.5 flex justify-between font-medium text-sm border-b border-gray-100">
                      <div className="flex items-center gap-2">
                        <MarketLogo slug={slug} size={20} />
                        <span>{MARKET_MAP[slug].name}</span>
                      </div>
                      <span className="font-bold">{data.total.toFixed(2)} ₺</span>
                    </div>
                    <div className="divide-y divide-gray-50 bg-white">
                      {data.items.map(({item, info}) => {
                        const g = GROUPS.find(x => x.id === item.groupId);
                        return (
                          <div key={item.id} className={"px-3 py-2 flex justify-between text-sm items-center " + (item.isChecked ? "opacity-40 line-through" : "")}>
                            <div>
                              <span className="mr-2">{g.emoji}</span>
                              {g.name} <span className="text-gray-500 text-xs">({info.brand})</span>
                            </div>
                            <div className="text-gray-600 font-medium">{(info.price * item.quantity).toFixed(2)} ₺</div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-2 pt-4 border-t border-gray-100">
               <button 
                  onClick={() => handleApplyPlan(mode)}
                  className={"w-full py-3 rounded-xl font-bold shadow-sm transition-colors flex items-center justify-center gap-2 " + 
                    (mode === "single" && !optimize.bestSingle ? "bg-gray-300 text-gray-500 cursor-not-allowed" : "bg-emerald-600 hover:bg-emerald-700 text-white")}
                >
                  <span>🛒</span> Bu Planı Alışveriş Listeme Uygula
                </button>
            </div>

            {mode === "combo" && optimize.cheapestComboTotal < optimize.comboTotal && (
              <button 
                onClick={() => { clearPreferences(list.id); setMode("cheapest"); }}
                className="mt-4 p-3 bg-orange-50 hover:bg-orange-100 transition-colors rounded-lg border border-orange-200 flex items-start gap-2 text-left w-full cursor-pointer group"
              >
                <span className="text-xl group-hover:scale-110 transition-transform">💡</span>
                <div className="text-xs text-orange-800 leading-tight">
                  Seçtiğiniz markalar yerine <b>MARKA FARKETMEZ</b> derseniz, tüm ürünlerin en ucuzunu alarak <b>{(optimize.comboTotal - optimize.cheapestComboTotal).toFixed(2)} ₺</b> daha az ödeyebilirsiniz. <u className="font-semibold ml-1">Uygulamak için tıklayın.</u>
                </div>
              </button>
            )}
          </div>
        </div>
      )}

      {pickerItem && pickerGroup && (
        <div className="fixed inset-0 bg-black/40 flex items-end z-50" onClick={() => setPickerItemId(null)}>
          <div className="bg-white w-full max-w-md mx-auto rounded-t-2xl p-4 max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <div>
                <div className="text-lg font-bold">{pickerGroup.name}</div>
                <div className="text-xs text-gray-500">Tercih ettiğiniz markayı seçin</div>
              </div>
              <button onClick={() => setPickerItemId(null)} className="text-gray-400 text-2xl">&times;</button>
            </div>

            <div className="space-y-2">
              <button onClick={() => { updateItem(list.id, pickerItem.id, { preferredProductId: null }); setPickerItemId(null); }}
                className={"w-full text-left p-3 rounded-lg border " + (!pickerItem.preferredProductId ? "border-emerald-500 bg-emerald-50" : "border-gray-200")}>
                <div className="font-semibold text-emerald-700">Farketmez (En Ucuzu Al)</div>
                <div className="text-xs text-gray-500">Otomatik olarak en uygun fiyatlı markayı seçer.</div>
              </button>

              {pickerAlternatives.map(p => (
                <button key={p.id} onClick={() => { updateItem(list.id, pickerItem.id, { preferredProductId: p.id }); setPickerItemId(null); }}
                  className={"w-full text-left p-3 rounded-lg border flex items-center justify-between " + (pickerItem.preferredProductId === p.id ? "border-emerald-500 bg-emerald-50" : "border-gray-200")}>
                  <div>
                    <div className="font-semibold flex items-center gap-2">
                       <MarketLogo slug={p.market} size={18} /> {p.brand}
                    </div>
                    <div className="text-xs text-gray-500">{MARKET_MAP[p.market].name}</div>
                  </div>
                  <div className="font-bold text-gray-800">{p.price.toFixed(2)} ₺</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

    </main>
  );
}
