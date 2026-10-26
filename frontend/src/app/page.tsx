"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, formatSize, num, GroupSummary } from "@/lib/api";
import { useGroupIcon, useLists } from "@/lib/store";
import MarketLogo from "@/components/MarketLogo";

export default function HomePage() {
  const { categories, marketById } = useLists();
  const groupIcon = useGroupIcon();
  const [q, setQ] = useState("");
  const [cat, setCat] = useState<number | null>(null); // null = Tümü
  const [results, setResults] = useState<GroupSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

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
      <div className="relative mb-3">
        <input value={q} onChange={e => setQ(e.target.value)}
          placeholder="Ürün ara (örn. süt, ekmek, deterjan)"
          className="w-full pl-10 pr-4 py-3 rounded-xl bg-white border border-gray-200 focus:outline-none focus:ring-2 focus:ring-emerald-500" />
        <span className="absolute left-3 top-3.5 text-gray-400">🔍</span>
      </div>
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
      {error && <div className="card p-4 text-sm text-red-600 mb-3">Ürünler yüklenemedi: {error}</div>}
      <div className="space-y-3">
        {(results || []).map(group => {
          const cheapest = [...group.market_prices].sort((a, b) => num(a.min_price) - num(b.min_price))[0];
          return (
            <Link key={group.id} href={"/products/" + group.id}
              className="card p-4 block hover:border-emerald-200">
              <div className="flex items-start gap-3">
                <div className="text-3xl">{groupIcon(group.category_id)}</div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900">{group.name}</div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {[formatSize(group.quantity, group.unit), group.market_prices.length + " market"].filter(Boolean).join(" · ")}
                  </div>
                  {cheapest && (
                    <div className="mt-2 flex items-center gap-2 text-sm">
                      <MarketLogo id={cheapest.market_id} size={20} />
                      <span className="text-gray-600">{marketById(cheapest.market_id)?.name}</span>
                      <span className="font-bold text-emerald-600">{num(cheapest.min_price).toFixed(2)} ₺</span>
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
