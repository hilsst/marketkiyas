"use client";
import { useEffect, useMemo, useState } from "react";
import { api, formatSize, num, unitPrice, GroupDetail, ListItem } from "@/lib/api";
import { useLists } from "@/lib/store";
import MarketLogo from "@/components/MarketLogo";

type Patch = Parameters<typeof api.updateItem>[2];

/** Kutuya basılı tutunca açılan pencere: marka (Farketmez/kilitli), adet, şube fiyatları, alarm, çıkar. */
export default function ItemSheet({
  groupId, icon, item, onClose, onPatch, onRemove, onAdd,
}: {
  groupId: number; icon: string; item?: ListItem | null; onClose: () => void;
  onPatch?: (patch: Patch) => void; onRemove?: () => void; onAdd?: () => void;
}) {
  const { marketById, setToast, refreshAlerts } = useLists();
  const [group, setGroup] = useState<GroupDetail | null>(null);

  useEffect(() => { api.productGroup(groupId).then(setGroup).catch(() => setGroup(null)); }, [groupId]);

  const brand = item?.preferred_brand ?? null;
  const qty = item ? num(item.quantity) : 0;

  // Seçili markanın (Farketmez ise tümünün) şube fiyatları, ucuzdan pahalıya
  const offers = useMemo(() => (group?.products || [])
    .filter(p => p.price != null && (brand == null || p.brand?.toLocaleLowerCase("tr") === brand.toLocaleLowerCase("tr")))
    .flatMap(p => p.store_prices.length
      ? p.store_prices.map(sp => ({ key: p.id + "-" + sp.store_id, marketId: p.market_id, label: sp.store_name, brand: p.brand, price: num(sp.price) }))
      : [{ key: String(p.id), marketId: p.market_id, label: p.store_name, brand: p.brand, price: num(p.price) }])
    .sort((a, b) => a.price - b.price), [group, brand]);
  const missingMarkets = useMemo(() => {
    if (!group || brand == null) return [];
    const have = new Set(offers.map(o => o.marketId));
    return Array.from(new Set(group.products.map(p => p.market_id))).filter(m => !have.has(m));
  }, [group, brand, offers]);

  const cheapest = group?.min_price != null ? num(group.min_price) : null;
  const perUnit = group && unitPrice(cheapest, group.quantity, group.unit);

  const setAlert = async () => {
    try {
      await api.createAlert(groupId);
      setToast("Fiyat düşünce haber vereceğiz 🔔");
      refreshAlerts();
    } catch (e) { setToast((e as Error).message); }
  };

  return (
    <div className="fixed inset-0 bg-black/45 flex items-end z-50" onClick={onClose}>
      <div className="bg-white w-full max-w-md mx-auto rounded-t-3xl p-5 max-h-[88vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
        <div className="flex items-center gap-3">
          <div className="w-16 h-16 rounded-2xl bg-emerald-600 flex items-center justify-center text-3xl shrink-0">{icon}</div>
          <div className="min-w-0">
            <div className="text-xl font-extrabold leading-tight">{group?.name || item?.group_name || "…"}</div>
            {cheapest != null && (
              <div className="text-xs text-gray-500 mt-0.5">
                En ucuz: <b className="text-emerald-700">{cheapest.toFixed(2)} ₺</b>
                {perUnit && " · " + perUnit.label}
                {group && formatSize(group.quantity, group.unit) && " · " + formatSize(group.quantity, group.unit)}
              </div>
            )}
          </div>
        </div>

        {item && onPatch && (
          <>
            <div className="text-xs font-bold text-gray-500 mt-5 mb-2">MARKA</div>
            <div className="flex flex-wrap gap-2 text-sm">
              <button onClick={() => onPatch({ preferred_product_id: null })}
                className={"px-3 py-2 rounded-xl " + (brand == null ? "bg-emerald-600 text-white font-semibold" : "border border-gray-200")}>
                Farketmez (en ucuz)
              </button>
              {(group?.brands || []).map(b => {
                const on = brand?.toLocaleLowerCase("tr") === b.toLocaleLowerCase("tr");
                return (
                  <button key={b} onClick={() => onPatch({ preferred_brand: b })}
                    className={"px-3 py-2 rounded-xl " + (on ? "bg-emerald-600 text-white font-semibold" : "border border-gray-200")}>
                    {on ? "🔒 " : ""}{b}
                  </button>
                );
              })}
              {group === null && <span className="text-xs text-gray-400 py-2">Yükleniyor…</span>}
            </div>

            <div className="text-xs font-bold text-gray-500 mt-5 mb-2">ADET</div>
            <div className="flex items-center gap-4">
              <button onClick={() => (qty > 1 ? onPatch({ quantity: qty - 1 }) : onRemove?.())}
                className="w-10 h-10 rounded-full bg-gray-100 text-xl">{qty > 1 ? "−" : "🗑"}</button>
              <span className="text-2xl font-extrabold w-8 text-center">{qty}</span>
              <button onClick={() => qty < 99 && onPatch({ quantity: qty + 1 })} className="w-10 h-10 rounded-full bg-gray-100 text-xl">+</button>
              {item.added_by_name && <span className="ml-auto text-xs text-sky-700">{item.added_by_name} ekledi</span>}
            </div>
          </>
        )}

        <div className="text-xs font-bold text-gray-500 mt-5 mb-2">MARKETLERDE{brand ? " (" + brand + ")" : ""}</div>
        <div className="divide-y divide-gray-100 text-sm border border-gray-100 rounded-xl">
          {offers.slice(0, 6).map((o, i) => (
            <div key={o.key} className="flex items-center gap-2 px-3 py-2">
              <MarketLogo id={o.marketId} size={18} />
              <span className="min-w-0 truncate">
                {marketById(o.marketId)?.name}{o.label ? " · " + o.label : ""}
                {brand == null && o.brand && <span className="text-gray-400 text-xs"> · {o.brand}</span>}
              </span>
              <b className={"ml-auto shrink-0 " + (i === 0 ? "text-emerald-700" : "")}>{o.price.toFixed(2)} ₺</b>
            </div>
          ))}
          {missingMarkets.map(m => (
            <div key={m} className="flex items-center gap-2 px-3 py-2">
              <MarketLogo id={m} size={18} /><span>{marketById(m)?.name}</span>
              <span className="ml-auto text-gray-400">yok</span>
            </div>
          ))}
          {group && offers.length === 0 && <div className="px-3 py-2 text-gray-400">Seçtiğiniz marketlerde yok</div>}
          {!group && <div className="px-3 py-2 text-gray-400">Yükleniyor…</div>}
        </div>

        <div className="mt-4 flex gap-2">
          <button onClick={setAlert} className="flex-1 bg-gray-100 rounded-xl py-3 text-sm font-semibold">🔔 Alarm kur</button>
          {item && onRemove ? (
            <button onClick={onRemove} className="flex-1 bg-red-50 text-red-600 rounded-xl py-3 text-sm font-semibold">Listeden çıkar</button>
          ) : onAdd ? (
            <button onClick={onAdd} className="flex-1 bg-emerald-600 text-white rounded-xl py-3 text-sm font-semibold">➕ Listeye ekle</button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
