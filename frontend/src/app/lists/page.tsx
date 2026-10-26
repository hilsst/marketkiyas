"use client";
import Link from "next/link";
import { useState } from "react";
import { useLists } from "@/lib/store";
import { PRODUCTS, MARKET_MAP } from "@/lib/demo-data";
import MarketLogo from "@/components/MarketLogo";

export default function ListsPage() {
  const { lists, createList, hydrated } = useLists();
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");

  if (!hydrated) return <div className="p-6">Yükleniyor…</div>;

  return (
    <main className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">📋 Listeler</h1>
        <button onClick={() => setCreating(true)} className="bg-emerald-600 text-white text-sm px-3 py-1.5 rounded-lg">+ Yeni</button>
      </div>
      {creating && (
        <div className="card p-3 mb-3">
          <input value={name} onChange={e => setName(e.target.value)} placeholder="Liste adı"
            className="w-full border rounded-lg px-3 py-2 mb-2" />
          <div className="flex gap-2">
            <button onClick={() => { if (name.trim()) { createList(name.trim()); setName(""); setCreating(false); } }}
              className="flex-1 bg-emerald-600 text-white py-2 rounded-lg">Kaydet</button>
            <button onClick={() => { setCreating(false); setName(""); }} className="px-4 bg-gray-100 rounded-lg">İptal</button>
          </div>
        </div>
      )}
      <div className="space-y-3">
        {lists.map(l => {
          const total = l.items.reduce((s, it) => {
            const prods = PRODUCTS.filter(p => p.groupId === it.groupId && p.inStock);
            return prods.length ? s + Math.min(...prods.map(p => p.price)) * it.quantity : s;
          }, 0);
          const counts = {};
          for (const it of l.items) {
            const prods = PRODUCTS.filter(p => p.groupId === it.groupId && p.inStock);
            if (!prods.length) continue;
            const min = prods.find(p => p.price === Math.min(...prods.map(x => x.price)));
            if (min) counts[min.market] = (counts[min.market] || 0) + 1;
          }
          const top = Object.entries(counts).sort((a,b) => b[1]-a[1])[0];
          return (
            <Link key={l.id} href={"/lists/" + l.id} className="card p-4 block hover:border-emerald-200">
              <div className="flex items-center justify-between">
                <div className="font-semibold">{l.name}</div>
                <div className="text-xs text-gray-400">{l.items.length} ürün</div>
              </div>
              <div className="text-sm text-gray-500 mt-1">
                Tahmini: <b className="text-gray-900">{total.toFixed(2)} ₺</b>
              </div>
              {top && (
                <div className="mt-2 flex items-center gap-2 text-xs">
                  <MarketLogo slug={top[0]} size={18} />
                  <span className="text-gray-600">En çok: {MARKET_MAP[top[0]].name}</span>
                </div>
              )}
            </Link>
          );
        })}
      </div>
    </main>
  );
}
