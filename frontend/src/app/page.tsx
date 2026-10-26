"use client";
import { useMemo, useState } from "react";
import Link from "next/link";
import { GROUPS, PRODUCTS, CATEGORIES, MARKET_MAP } from "@/lib/demo-data";
import MarketLogo from "@/components/MarketLogo";

export default function HomePage() {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("Tümü");

  const results = useMemo(() =>
    GROUPS
      .filter(g => cat === "Tümü" || g.category === cat)
      .filter(g => !q || g.name.toLowerCase().includes(q.toLowerCase()))
      .map(g => {
        const prods = PRODUCTS.filter(p => p.groupId === g.id && p.inStock)
          .sort((a, b) => a.price - b.price);
        return { group: g, count: prods.length, cheapest: prods[0] };
      }), [q, cat]);

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
        {CATEGORIES.map(c => (
          <button key={c} onClick={() => setCat(c)}
            className={"whitespace-nowrap px-3 py-1.5 text-sm rounded-full border " + (cat===c
              ? "bg-emerald-600 text-white border-emerald-600"
              : "bg-white text-gray-700 border-gray-200")}>
            {c}
          </button>
        ))}
      </div>
      <div className="space-y-3">
        {results.map(({ group, count, cheapest }) => (
          <Link key={group.id} href={"/products/" + group.id}
            className="card p-4 block hover:border-emerald-200">
            <div className="flex items-start gap-3">
              <div className="text-3xl">{group.emoji}</div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-gray-900">{group.name}</div>
                <div className="text-xs text-gray-500 mt-0.5">{group.display} · {count} market</div>
                {cheapest && (
                  <div className="mt-2 flex items-center gap-2 text-sm">
                    <MarketLogo slug={cheapest.market} size={20} />
                    <span className="text-gray-600">{MARKET_MAP[cheapest.market].name}</span>
                    <span className="font-bold text-emerald-600">{cheapest.price.toFixed(2)} ₺</span>
                    {cheapest.isPromo && (
                      <span className="text-xs bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded">PROMO</span>
                    )}
                  </div>
                )}
              </div>
              <div className="text-gray-300">›</div>
            </div>
          </Link>
        ))}
        {results.length === 0 && (
          <div className="text-center text-gray-500 py-12">
            <div className="text-4xl mb-2">🔍</div>
            <div>Sonuç bulunamadı</div>
          </div>
        )}
      </div>
    </main>
  );
}
