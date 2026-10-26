"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, formatSize, num, unitPrice, Deal } from "@/lib/api";
import { useGroupIcon, useLists } from "@/lib/store";
import MarketLogo from "@/components/MarketLogo";
import ProductImage from "@/components/ProductImage";

export default function DealsPage() {
  const { user, marketById, categories } = useLists();
  const groupIcon = useGroupIcon();
  const [deals, setDeals] = useState<Deal[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [market, setMarket] = useState<number | null>(null); // null = Tümü
  const [cat, setCat] = useState<number | null>(null);

  useEffect(() => {
    api.deals().then(d => { setDeals(d); setError(null); }).catch(e => setError(e.message));
  }, [user]);

  const marketIds = useMemo(() => Array.from(new Set((deals || []).map(d => d.market_id))), [deals]);
  const catIds = useMemo(() => new Set((deals || []).map(d => d.category_id)), [deals]);
  const shown = (deals || []).filter(d => (market == null || d.market_id === market) && (cat == null || d.category_id === cat));

  const chip = (active: boolean) =>
    "whitespace-nowrap px-3 py-1.5 text-sm rounded-full border flex items-center gap-1.5 " +
    (active ? "bg-emerald-600 text-white border-emerald-600" : "bg-white text-gray-700 border-gray-200");

  return (
    <main className="p-4">
      <h1 className="text-2xl font-bold mb-1">🏷️ Fırsatlar</h1>
      <p className="text-xs text-gray-500 mb-3">
        {user ? "Seçtiğiniz marketlerde" : "Marketlerde"} son 30 güne göre ucuzlayan ve kampanyadaki ürünler.
      </p>

      {marketIds.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-2 -mx-4 px-4">
          <button onClick={() => setMarket(null)} className={chip(market == null)}>Tüm marketler</button>
          {marketIds.map(id => (
            <button key={id} onClick={() => setMarket(id)} className={chip(market === id)}>
              <MarketLogo id={id} size={16} /> {marketById(id)?.name}
            </button>
          ))}
        </div>
      )}
      {catIds.size > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-3 -mx-4 px-4">
          <button onClick={() => setCat(null)} className={chip(cat == null)}>Tümü</button>
          {categories.filter(c => catIds.has(c.id)).map(c => (
            <button key={c.id} onClick={() => setCat(c.id)} className={chip(cat === c.id)}>{c.icon} {c.name}</button>
          ))}
        </div>
      )}

      {error && <div className="card p-4 text-sm text-red-600 mb-3">Fırsatlar yüklenemedi: {error}</div>}
      {deals === null && !error && <div className="text-center text-gray-400 py-12">Yükleniyor…</div>}
      {deals?.length === 0 && (
        <div className="card p-6 text-center text-gray-500">
          <div className="text-3xl mb-2">🏷️</div>
          <div className="text-sm">Şu an indirimde ürün yok</div>
          <div className="text-xs mt-1">Fiyatlar her güncellendiğinde bu sayfa yenilenir.</div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        {shown.map(d => {
          const perUnit = unitPrice(d.price, d.quantity, d.unit);
          return (
            <Link key={d.group_id} href={"/products/" + d.group_id} className="card p-3 flex flex-col relative hover:border-emerald-200">
              <span className="absolute top-2 right-2 bg-red-500 text-white text-xs font-bold px-1.5 py-0.5 rounded">
                %{d.discount_percent}
              </span>
              <div className="flex justify-center mb-2">
                <ProductImage src={d.image_url} icon={groupIcon(d.category_id)} size={64} />
              </div>
              <div className="text-sm font-semibold leading-tight line-clamp-2">{d.group_name}</div>
              <div className="text-[11px] text-gray-500 truncate">
                {[d.brand, formatSize(d.quantity, d.unit)].filter(Boolean).join(" · ")}
              </div>
              <div className="mt-auto pt-2">
                <div className="text-xs text-gray-400 line-through">{num(d.previous_price).toFixed(2)} ₺</div>
                <div className="flex items-center gap-1.5">
                  <MarketLogo id={d.market_id} size={18} />
                  <span className="font-bold text-emerald-600">{num(d.price).toFixed(2)} ₺</span>
                </div>
                {perUnit && <div className="text-[10px] text-gray-400">{perUnit.label}</div>}
                {d.is_campaign && <div className="text-[10px] text-orange-600 font-semibold mt-0.5">KAMPANYA</div>}
              </div>
            </Link>
          );
        })}
      </div>
    </main>
  );
}
