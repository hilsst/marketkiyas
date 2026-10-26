"use client";
import { useParams, useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { GROUPS, PRODUCTS, MARKET_MAP, priceHistory } from "@/lib/demo-data";
import MarketLogo from "@/components/MarketLogo";
import { useLists } from "@/lib/store";

export default function ProductDetailPage() {
  const params = useParams();
  const router = useRouter();
  const groupId = Number(params.id);
  const group = GROUPS.find(g => g.id === groupId);
  const products = useMemo(() =>
    PRODUCTS.filter(p => p.groupId === groupId).sort((a, b) => a.price - b.price),
    [groupId]);
  const [selected, setSelected] = useState(products[0]);
  const { lists, addItem, setToast } = useLists();
  const [picker, setPicker] = useState(false);

  if (!group) return <div className="p-6 text-center">Ürün bulunamadı</div>;

  const hist = priceHistory(selected.id, selected.price);
  const minH = Math.min(...hist), maxH = Math.max(...hist);
  const range = maxH - minH || 1, w = 320, h = 80;
  const pts = hist.map((v, i) => (i/(hist.length-1))*w + "," + (h-((v-minH)/range)*(h-10)-5)).join(" ");

  function handleAddToList(listId: number) {
    addItem(listId, group!.id, selected.id);
    setToast(group!.name + " eklendi");
    setPicker(false);
    router.push("/"); // Ana sayfaya geri dön
  }

  return (
    <main className="p-4">
      <button onClick={() => router.back()} className="text-gray-600 mb-3">← Geri</button>
      <div className="card p-4 mb-3">
        <div className="flex items-start gap-3">
          <div className="text-5xl">{group.emoji}</div>
          <div>
            <h1 className="text-xl font-bold">{group.name}</h1>
            <div className="text-sm text-gray-500">{group.display} · {group.category}</div>
          </div>
        </div>
      </div>
      <div className="card p-4 mb-3">
        <div className="text-xs text-gray-500 mb-1">Son 30 gün</div>
        <svg viewBox={"0 0 " + w + " " + h} className="w-full h-20">
          <polyline fill="none" stroke="#059669" strokeWidth="2" points={pts} strokeLinejoin="round" />
          <polygon fill="#05966920" points={"0," + h + " " + pts + " " + w + "," + h} />
        </svg>
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>En düşük: {minH.toFixed(2)} ₺</span>
          <span className="font-semibold text-emerald-600">Şu an: {selected.price.toFixed(2)} ₺</span>
        </div>
      </div>
      <div className="card divide-y divide-gray-100 mb-4">
        <div className="px-4 py-3 text-sm font-semibold text-gray-700">{products.length} markette bulundu</div>
        {products.map((p, idx) => (
          <button key={p.id} onClick={() => setSelected(p)}
            className={"w-full px-4 py-3 flex items-center gap-3 text-left hover:bg-gray-50 " + (p.id===selected.id?"bg-emerald-50/50":"")}>
            <MarketLogo slug={p.market} size={32} />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{MARKET_MAP[p.market].name}</span>
                <span className="text-xs text-gray-500">· {p.brand}</span>
              </div>
              {p.isPromo && p.oldPrice && (
                <div className="text-xs text-orange-600 mt-0.5">
                  <span className="line-through text-gray-400">{p.oldPrice.toFixed(2)}</span> promo
                </div>
              )}
            </div>
            <div className="text-right">
              <div className={"font-bold " + (idx===0?"text-emerald-600":"text-gray-900")}>{p.price.toFixed(2)} ₺</div>
              {idx === 0 && <div className="text-[10px] text-emerald-600 font-semibold">EN UCUZ</div>}
            </div>
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <button onClick={() => setPicker(true)} className="flex-1 bg-emerald-600 text-white py-3 rounded-xl font-semibold">
          ➕ Listeye Ekle
        </button>
        <button className="px-4 bg-white border border-gray-200 rounded-xl">🔔</button>
      </div>
      {picker && (
        <div className="fixed inset-0 bg-black/40 flex items-end z-50" onClick={() => setPicker(false)}>
          <div className="bg-white w-full max-w-md mx-auto rounded-t-2xl p-4" onClick={e => e.stopPropagation()}>
            <div className="text-lg font-bold mb-3">Hangi listeye?</div>
            <div className="space-y-2">
              {lists.map(l => (
                <button key={l.id} onClick={() => handleAddToList(l.id)} 
                  className="w-full text-left p-3 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors">
                  <div className="font-medium">{l.name}</div>
                  <div className="text-xs text-gray-500">{l.items.length} ürün</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
