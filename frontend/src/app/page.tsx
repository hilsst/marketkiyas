"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, formatSize, num, unitPrice, GroupSummary } from "@/lib/api";
import { useGroupIcon, useLists } from "@/lib/store";
import MarketLogo from "@/components/MarketLogo";
import ProductImage from "@/components/ProductImage";
import BarcodeScanner from "@/components/BarcodeScanner";

const cheapestOf = (g: GroupSummary) => [...g.market_prices].sort((a, b) => num(a.min_price) - num(b.min_price))[0];
const unitValue = (g: GroupSummary) => unitPrice(cheapestOf(g)?.min_price, g.quantity, g.unit)?.value ?? Infinity;

export default function HomePage() {
  const { categories, marketById } = useLists();
  const groupIcon = useGroupIcon();
  const [q, setQ] = useState("");
  const [cat, setCat] = useState<number | null>(null); // null = Tümü
  const [results, setResults] = useState<GroupSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  // "Birim fiyat": 400 g ile 1 kg'ı kilo başına fiyatla karşılaştırır
  const [byUnit, setByUnit] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(() => {
      api.searchProducts(q.trim(), cat)
        .then(r => { if (!cancelled) { setResults(r); setError(null); } })
        .catch(e => { if (!cancelled) setError(e.message); });
    }, q ? 250 : 0);
    return () => { cancelled = true; clearTimeout(t); };
  }, [q, cat]);

  const chips: [number | null, string][] = [[null, "Tümü"], ...categories.map(c => [c.id, c.name] as [number, string])];

  return (
    <main className="p-4">
      <h1 className="text-2xl font-bold mb-4">🛒 MarketKıyas</h1>
      <div className="flex gap-2 mb-3">
        <div className="relative flex-1">
          <input value={q} onChange={e => setQ(e.target.value)}
            placeholder="Ürün ara (örn. süt, ekmek, deterjan)"
            className="w-full pl-10 pr-4 py-3 rounded-xl bg-white border border-gray-200 focus:outline-none focus:ring-2 focus:ring-emerald-500" />
          <span className="absolute left-3 top-3.5 text-gray-400">🔍</span>
        </div>
        <button onClick={() => setScanning(true)} aria-label="Barkod okut"
          className="px-3 rounded-xl bg-white border border-gray-200 text-xs font-medium text-gray-700 flex flex-col items-center justify-center">
          <span className="text-lg leading-none">▥</span>Barkod
        </button>
      </div>
      {scanning && <BarcodeScanner onClose={() => setScanning(false)} />}
      <div className="flex gap-2 overflow-x-auto pb-3 -mx-4 px-4 mb-2">
        {chips.map(([id, name]) => (
          <button key={id ?? "all"} onClick={() => setCat(id)}
            className={"whitespace-nowrap px-3 py-1.5 text-sm rounded-full border " + (cat===id
              ? "bg-emerald-600 text-white border-emerald-600"
              : "bg-white text-gray-700 border-gray-200")}>
            {name}
          </button>
        ))}
      </div>
      {(results?.length ?? 0) > 1 && (
        <div className="flex justify-end mb-2 -mt-1">
          <button onClick={() => setByUnit(v => !v)}
            className={"text-xs px-2.5 py-1 rounded-full border " + (byUnit ? "bg-emerald-50 border-emerald-300 text-emerald-700" : "bg-white border-gray-200 text-gray-600")}>
            {byUnit ? "✓ " : ""}Kilo/litre fiyatına göre sırala
          </button>
        </div>
      )}
      {error && <div className="card p-4 text-sm text-red-600 mb-3">Ürünler yüklenemedi: {error}</div>}
      <div className="space-y-3">
        {(byUnit && results ? [...results].sort((a, b) => unitValue(a) - unitValue(b)) : results || []).map(group => {
          const cheapest = cheapestOf(group);
          const perUnit = cheapest && unitPrice(cheapest.min_price, group.quantity, group.unit);
          return (
            <Link key={group.id} href={"/products/" + group.id}
              className="card p-4 block hover:border-emerald-200">
              <div className="flex items-start gap-3">
                <ProductImage src={group.image_url} icon={groupIcon(group.category_id)} size={48} />
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900">{group.name}</div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {[formatSize(group.quantity, group.unit), group.market_prices.length + " market"].filter(Boolean).join(" · ")}
                  </div>
                  {cheapest && (
                    <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-sm">
                      <MarketLogo id={cheapest.market_id} size={20} />
                      <span className="text-gray-600">{marketById(cheapest.market_id)?.name}</span>
                      <span className="font-bold text-emerald-600 whitespace-nowrap">{num(cheapest.min_price).toFixed(2)} ₺</span>
                      {perUnit && <span className="text-xs text-gray-400 whitespace-nowrap">({perUnit.label})</span>}
                      {cheapest.regular_price && (
                        <span className="text-xs bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded">PROMO</span>
                      )}
                    </div>
                  )}
                </div>
                <div className="text-gray-300">›</div>
              </div>
            </Link>
          );
        })}
        {results === null && !error && <div className="text-center text-gray-400 py-12">Yükleniyor…</div>}
        {results?.length === 0 && (
          <div className="text-center text-gray-500 py-12">
            <div className="text-4xl mb-2">🔍</div>
            <div>Sonuç bulunamadı</div>
          </div>
        )}
      </div>
    </main>
  );
}
