"use client";
import { useMemo, useState } from "react";
import { formatSize, num, unitPrice, GroupSummary, MarketPrice } from "@/lib/api";
import MarketLogo from "@/components/MarketLogo";

export type SortKey = "recommended" | "cheapest" | "unit" | "discount";

/** Arama ve kategori listesinin filtresi; tamamı tarayıcıda, yüklenen ürünler üzerinde çalışır. */
export interface Filters {
  sort: SortKey;
  markets: number[]; // boş = hepsi
  brands: string[];
  discountedOnly: boolean;
  sizes: string[]; // formatSize etiketi: "1 L", "500 g"
}

export const DEFAULT_FILTERS: Filters = { sort: "recommended", markets: [], brands: [], discountedOnly: false, sizes: [] };

const SORTS: [SortKey, string][] = [
  ["recommended", "Önerilen"],
  ["cheapest", "En ucuz"],
  ["unit", "Kilo/litre fiyatı en ucuz"],
  ["discount", "İndirim oranı en yüksek"],
];

/** Sıralamayı saymadan açık filtre sayısı ("Filtre · 2") */
export const activeFilterCount = (f: Filters) =>
  (f.sort !== "recommended" ? 1 : 0) + f.markets.length + f.brands.length + (f.discountedOnly ? 1 : 0) + f.sizes.length;

/** Market filtresi açıksa yalnızca o marketlerin fiyatları geçerlidir */
export const visiblePrices = (g: GroupSummary, f: Filters): MarketPrice[] =>
  f.markets.length ? g.market_prices.filter(m => f.markets.includes(m.market_id)) : g.market_prices;

export const cheapestPrice = (g: GroupSummary, f: Filters = DEFAULT_FILTERS) =>
  [...visiblePrices(g, f)].sort((a, b) => num(a.min_price) - num(b.min_price))[0];

const discountOf = (g: GroupSummary, f: Filters) =>
  Math.max(0, ...visiblePrices(g, f).map(m =>
    m.regular_price && num(m.regular_price) > num(m.min_price) ? 1 - num(m.min_price) / num(m.regular_price) : 0));

export function applyFilters(results: GroupSummary[], f: Filters): GroupSummary[] {
  const brands = new Set(f.brands.map(b => b.toLocaleLowerCase("tr")));
  const out = results.filter(g =>
    visiblePrices(g, f).length > 0
    && (!brands.size || g.brands.some(b => brands.has(b.toLocaleLowerCase("tr"))))
    && (!f.discountedOnly || discountOf(g, f) > 0)
    && (!f.sizes.length || f.sizes.includes(formatSize(g.quantity, g.unit))));
  const price = (g: GroupSummary) => num(cheapestPrice(g, f)?.min_price ?? Infinity);
  const perUnit = (g: GroupSummary) => unitPrice(cheapestPrice(g, f)?.min_price, g.quantity, g.unit)?.value ?? Infinity;
  if (f.sort === "cheapest") out.sort((a, b) => price(a) - price(b));
  if (f.sort === "unit") out.sort((a, b) => perUnit(a) - perUnit(b));
  if (f.sort === "discount") out.sort((a, b) => discountOf(b, f) - discountOf(a, f) || price(a) - price(b));
  return out;
}

/** Alttan açılan filtre penceresi: sıralama, market, marka, indirim, boyut. Seçenekler yüklü ürünlerden çıkar. */
export function FilterSheet({
  results, value, onChange, onClose, marketName,
}: {
  results: GroupSummary[]; value: Filters; onChange: (f: Filters) => void; onClose: () => void;
  marketName: (id: number) => string | undefined;
}) {
  const [brandQuery, setBrandQuery] = useState("");
  const markets = useMemo(() => Array.from(new Set(results.flatMap(g => g.market_prices.map(m => m.market_id)))).sort((a, b) => a - b), [results]);
  const brands = useMemo(() => {
    const count = new Map<string, number>();
    results.forEach(g => g.brands.forEach(b => count.set(b, (count.get(b) || 0) + 1)));
    return Array.from(count.entries()).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "tr")).map(([b]) => b);
  }, [results]);
  const sizes = useMemo(() => {
    // Birim birim, küçükten büyüğe: 200 ml, 500 ml, 1 L … 500 g, 1 kg
    const seen = new Map<string, [string, number]>();
    results.forEach(g => { const s = formatSize(g.quantity, g.unit); if (s) seen.set(s, [g.unit || "", num(g.quantity)]); });
    return Array.from(seen.entries())
      .sort((a, b) => a[1][0].localeCompare(b[1][0]) || a[1][1] - b[1][1])
      .map(([s]) => s);
  }, [results]);

  const toggle = <T,>(list: T[], v: T) => (list.includes(v) ? list.filter(x => x !== v) : [...list, v]);
  const chip = (on: boolean) => "px-3 py-1.5 rounded-full text-sm border " + (on ? "bg-emerald-600 text-white border-emerald-600" : "bg-white text-gray-700 border-gray-200");
  const shownBrands = brands.filter(b => b.toLocaleLowerCase("tr").includes(brandQuery.toLocaleLowerCase("tr"))).slice(0, 40);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-end z-50" onClick={onClose}>
      <div className="bg-white w-full max-w-md mx-auto rounded-t-2xl p-4 max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-3">
          <div className="text-lg font-bold">Filtre</div>
          <button onClick={() => onChange(DEFAULT_FILTERS)} className="text-sm text-emerald-700 font-medium">Temizle</button>
        </div>

        <div className="text-xs font-bold text-gray-500 mb-2">SIRALA</div>
        <div className="space-y-1 mb-4">
          {SORTS.map(([key, label]) => (
            <label key={key} className="flex items-center gap-3 py-1.5 text-sm">
              <input type="radio" name="sort" checked={value.sort === key} onChange={() => onChange({ ...value, sort: key })} className="accent-emerald-600 w-4 h-4" />
              {label}
            </label>
          ))}
        </div>

        {markets.length > 1 && (
          <>
            <div className="text-xs font-bold text-gray-500 mb-2">MARKET</div>
            <div className="flex flex-wrap gap-2 mb-4">
              {markets.map(id => (
                <button key={id} onClick={() => onChange({ ...value, markets: toggle(value.markets, id) })}
                  className={chip(value.markets.includes(id)) + " flex items-center gap-1.5"}>
                  <MarketLogo id={id} size={18} /> {marketName(id)}
                </button>
              ))}
            </div>
          </>
        )}

        {brands.length > 0 && (
          <>
            <div className="text-xs font-bold text-gray-500 mb-2">MARKA</div>
            {brands.length > 8 && (
              <input value={brandQuery} onChange={e => setBrandQuery(e.target.value)} placeholder="Marka ara"
                className="w-full mb-2 px-3 py-2 rounded-lg bg-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500" />
            )}
            <div className="flex flex-wrap gap-2 mb-4">
              {value.brands.filter(b => !shownBrands.includes(b)).concat(shownBrands).map(b => (
                <button key={b} onClick={() => onChange({ ...value, brands: toggle(value.brands, b) })} className={chip(value.brands.includes(b))}>{b}</button>
              ))}
            </div>
          </>
        )}

        <label className="flex items-center justify-between py-2 mb-3 text-sm font-medium">
          Yalnızca indirimdekiler
          <input type="checkbox" checked={value.discountedOnly} onChange={e => onChange({ ...value, discountedOnly: e.target.checked })} className="accent-emerald-600 w-5 h-5" />
        </label>

        {sizes.length > 1 && (
          <>
            <div className="text-xs font-bold text-gray-500 mb-2">BOYUT</div>
            <div className="flex flex-wrap gap-2 mb-4">
              {sizes.map(s => (
                <button key={s} onClick={() => onChange({ ...value, sizes: toggle(value.sizes, s) })} className={chip(value.sizes.includes(s))}>{s}</button>
              ))}
            </div>
          </>
        )}

        <button onClick={onClose} className="w-full bg-emerald-600 text-white py-3 rounded-xl font-semibold">
          {applyFilters(results, value).length} ürünü göster
        </button>
      </div>
    </div>
  );
}
