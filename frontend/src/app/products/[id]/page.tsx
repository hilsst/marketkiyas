"use client";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api, formatSize, num, GroupDetail, GroupProduct } from "@/lib/api";
import MarketLogo from "@/components/MarketLogo";
import ProductImage from "@/components/ProductImage";
import { useGroupIcon, useLists } from "@/lib/store";

export default function ProductDetailPage() {
  const params = useParams();
  const router = useRouter();
  const groupId = Number(params.id);
  const { user, lists, addItem, setToast, marketById, categoryById } = useLists();
  const groupIcon = useGroupIcon();
  const [group, setGroup] = useState<GroupDetail | null | undefined>(undefined);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [picker, setPicker] = useState(false);

  useEffect(() => {
    api.productGroup(groupId).then(setGroup).catch(() => setGroup(null));
  }, [groupId]);

  // Yalnızca fiyatı olanlar; API fiyata göre sıralı döner
  const products = useMemo(() => (group?.products || []).filter(p => p.price != null), [group]);
  const selected: GroupProduct | undefined = products.find(p => p.id === selectedId) || products[0];
  // Şube seçildiyse her şubedeki fiyat ayrı satır ("CarrefourSA · Göksu Süper"), seçilmediyse zincir başına bir satır
  const offers = useMemo(() => products
    .flatMap(p => p.store_prices.length
      ? p.store_prices.map(sp => ({ key: p.id + "-" + sp.store_id, product: p, storeName: sp.store_name as string | null, price: num(sp.price) }))
      : [{ key: String(p.id), product: p, storeName: p.store_name, price: num(p.price) }])
    .sort((a, b) => a.price - b.price), [products]);
  const marketCount = new Set(products.map(p => p.market_id)).size;

  if (group === undefined) return <div className="p-6">Yükleniyor…</div>;
  if (!group) return <div className="p-6 text-center">Ürün bulunamadı</div>;

  const hist = selected ? selected.price_history.map(p => num(p.price)) : [];
  if (selected && hist.length === 0) hist.push(num(selected.price));
  if (hist.length === 1) hist.push(hist[0]);
  const minH = Math.min(...hist), maxH = Math.max(...hist);
  const range = maxH - minH || 1, w = 320, h = 80;
  const pts = hist.map((v, i) => (i/(hist.length-1))*w + "," + (h-((v-minH)/range)*(h-10)-5)).join(" ");

  async function handleAddToList(listId: number) {
    try {
      await addItem(listId, group!.id, selected?.id ?? null);
      setToast(group!.name + " eklendi");
      setPicker(false);
      router.push("/"); // Ana sayfaya geri dön
    } catch (e) {
      setToast((e as Error).message);
    }
  }

  const openPicker = () => {
    if (!user) { router.push("/login?next=" + encodeURIComponent("/products/" + groupId)); return; }
    setPicker(true);
  };

  return (
    <main className="p-4">
      <button onClick={() => router.back()} className="text-gray-600 mb-3">← Geri</button>
      <div className="card p-4 mb-3">
        <div className="flex items-start gap-3">
          <ProductImage src={selected?.image_url || group.image_url} icon={groupIcon(group.category_id)} size={72} />
          <div>
            <h1 className="text-xl font-bold">{group.name}</h1>
            <div className="text-sm text-gray-500">
              {[formatSize(group.quantity, group.unit), categoryById(group.category_id)?.name].filter(Boolean).join(" · ")}
            </div>
          </div>
        </div>
      </div>
      {selected && (
        <div className="card p-4 mb-3">
          <div className="text-xs text-gray-500 mb-1">Son 30 gün</div>
          <svg viewBox={"0 0 " + w + " " + h} className="w-full h-20">
            <polyline fill="none" stroke="#059669" strokeWidth="2" points={pts} strokeLinejoin="round" />
            <polygon fill="#05966920" points={"0," + h + " " + pts + " " + w + "," + h} />
          </svg>
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>En düşük: {minH.toFixed(2)} ₺</span>
            <span className="font-semibold text-emerald-600">Şu an: {num(selected.price).toFixed(2)} ₺</span>
          </div>
        </div>
      )}
      <div className="card divide-y divide-gray-100 mb-4">
        <div className="px-4 py-3 text-sm font-semibold text-gray-700">
          {marketCount} markette{offers.length > marketCount ? ", " + offers.length + " şubede" : ""} bulundu
        </div>
        {offers.map(({ key, product: p, storeName, price }, idx) => (
          <button key={key} onClick={() => setSelectedId(p.id)}
            className={"w-full px-4 py-3 flex items-center gap-3 text-left hover:bg-gray-50 " + (p.id===selected?.id?"bg-emerald-50/50":"")}>
            <MarketLogo id={p.market_id} size={32} />
            <div className="flex-1 min-w-0">
              <div className="text-sm">
                <span className="font-medium">{marketById(p.market_id)?.name}</span>
                {storeName && <span className="text-gray-500"> · {storeName}</span>}
              </div>
              <div className="text-xs text-gray-500 truncate">{p.brand ? p.brand + " · " : ""}{p.name}</div>
              {p.regular_price && (
                <div className="text-xs text-orange-600 mt-0.5">
                  <span className="line-through text-gray-400">{num(p.regular_price).toFixed(2)}</span> promo
                </div>
              )}
            </div>
            <div className="text-right">
              <div className={"font-bold " + (idx===0?"text-emerald-600":"text-gray-900")}>{price.toFixed(2)} ₺</div>
              {idx === 0 && <div className="text-[10px] text-emerald-600 font-semibold">EN UCUZ</div>}
            </div>
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <button onClick={openPicker} className="flex-1 bg-emerald-600 text-white py-3 rounded-xl font-semibold">
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
                  <div className="text-xs text-gray-500">{l.item_count} ürün</div>
                </button>
              ))}
              {lists.length === 0 && (
                <button onClick={() => router.push("/lists")} className="w-full text-left p-3 rounded-lg bg-gray-50 text-sm text-gray-600">
                  Henüz listeniz yok. Listeler sayfasından bir liste oluşturun.
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
