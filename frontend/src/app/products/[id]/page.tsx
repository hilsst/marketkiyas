"use client";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api, formatSize, num, unitPrice, GroupDetail, GroupProduct, PriceAlert } from "@/lib/api";
import MarketLogo from "@/components/MarketLogo";
import ProductImage from "@/components/ProductImage";
import { useGroupIcon, useLists } from "@/lib/store";

export default function ProductDetailPage() {
  const params = useParams();
  const router = useRouter();
  const groupId = Number(params.id);
  const { user, lists, addItem, setToast, marketById, categoryById, refreshAlerts } = useLists();
  const groupIcon = useGroupIcon();
  const [group, setGroup] = useState<GroupDetail | null | undefined>(undefined);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [picker, setPicker] = useState(false);
  const [alertSheet, setAlertSheet] = useState(false);
  const [alert, setAlert] = useState<PriceAlert | null>(null);
  const [target, setTarget] = useState("");

  useEffect(() => {
    api.productGroup(groupId).then(setGroup).catch(() => setGroup(null));
  }, [groupId]);

  useEffect(() => {
    if (!user) { setAlert(null); return; }
    api.alerts().then(all => setAlert(all.find(a => a.group_id === groupId) || null)).catch(() => {});
  }, [user, groupId]);

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
  const storeCount = new Set(products.flatMap(p => p.store_prices.map(sp => sp.store_id))).size;

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

  const openAlertSheet = () => {
    if (!user) { router.push("/login?next=" + encodeURIComponent("/products/" + groupId)); return; }
    setTarget(alert?.target_price ? num(alert.target_price).toFixed(2) : "");
    setAlertSheet(true);
  };

  async function saveAlert(withTarget: boolean) {
    const value = Number(target.replace(",", "."));
    if (withTarget && !(value > 0)) { setToast("Geçerli bir fiyat yazın"); return; }
    try {
      // Uygulama açıkken fiyat düşerse telefon bildirimi de gösterebilmek için izin istenir
      if (typeof Notification !== "undefined" && Notification.permission === "default") {
        Notification.requestPermission().catch(() => {});
      }
      const all = await api.createAlert(groupId, withTarget ? value : null, selectedId);
      setAlert(all.find(a => a.group_id === groupId) || null);
      setAlertSheet(false);
      setToast(withTarget ? "Fiyat " + value.toFixed(2) + " ₺ altına inince haber vereceğiz" : "Fiyat düşünce haber vereceğiz");
      refreshAlerts();
    } catch (e) { setToast((e as Error).message); }
  }

  async function removeAlert() {
    if (!alert) return;
    try {
      await api.deleteAlert(alert.id);
      setAlert(null);
      setAlertSheet(false);
      setToast("Alarm kaldırıldı");
      refreshAlerts();
    } catch (e) { setToast((e as Error).message); }
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
          {marketCount} markette{storeCount > marketCount ? ", " + storeCount + " şubede" : ""} bulundu
          {offers.length > Math.max(storeCount, marketCount) ? " · " + offers.length + " seçenek" : ""}
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
              {unitPrice(price, group.quantity, group.unit) && (
                <div className="text-[10px] text-gray-400">{unitPrice(price, group.quantity, group.unit)!.label}</div>
              )}
              {idx === 0 && <div className="text-[10px] text-emerald-600 font-semibold">EN UCUZ</div>}
            </div>
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <button onClick={openPicker} className="flex-1 bg-emerald-600 text-white py-3 rounded-xl font-semibold">
          ➕ Listeye Ekle
        </button>
        <button onClick={openAlertSheet} aria-label="Fiyat alarmı"
          className={"px-4 rounded-xl border text-sm " + (alert ? "bg-amber-50 border-amber-300 text-amber-800" : "bg-white border-gray-200")}>
          🔔{alert ? " Kurulu" : ""}
        </button>
      </div>
      {alertSheet && (
        <div className="fixed inset-0 bg-black/40 flex items-end z-50" onClick={() => setAlertSheet(false)}>
          <div className="bg-white w-full max-w-md mx-auto rounded-t-2xl p-4" onClick={e => e.stopPropagation()}>
            <div className="text-lg font-bold">Fiyat alarmı</div>
            <div className="text-xs text-gray-500 mb-4">
              {selectedId != null && selected
                ? <>Seçtiğin ürün takip edilecek: <b>{selected.brand || selected.name}</b> ({marketById(selected.market_id)?.name}). Fiyatı düşünce 🔔 sekmesinde haber veririz.</>
                : <>{group.name} şu an en ucuz {offers[0] ? offers[0].price.toFixed(2) + " ₺" : "-"}. Belli bir markayı takip etmek için önce o satırı seç.</>}
            </div>
            <button onClick={() => saveAlert(false)}
              className="w-full text-left p-3 rounded-lg border border-gray-200 hover:border-emerald-400 mb-2">
              <div className="font-semibold text-emerald-700">Fiyatı düşünce haber ver</div>
              <div className="text-xs text-gray-500">Şu anki en ucuz fiyatın altına inince</div>
            </button>
            <div className="p-3 rounded-lg border border-gray-200">
              <div className="font-semibold text-gray-800 mb-2">Şu fiyatın altına inince</div>
              <div className="flex gap-2">
                <input value={target} onChange={e => setTarget(e.target.value)} inputMode="decimal" placeholder="örn. 30,00"
                  className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm" />
                <button onClick={() => saveAlert(true)} className="bg-emerald-600 text-white px-4 rounded-lg text-sm font-semibold">Kur</button>
              </div>
            </div>
            {alert && (
              <button onClick={removeAlert} className="w-full mt-3 text-sm text-red-500 underline">Alarmı kaldır</button>
            )}
          </div>
        </div>
      )}
      {picker && (
        <div className="fixed inset-0 bg-black/40 flex items-end z-50" onClick={() => setPicker(false)}>
          <div className="bg-white w-full max-w-md mx-auto rounded-t-2xl p-4" onClick={e => e.stopPropagation()}>
            <div className="text-lg font-bold mb-3">Hangi listeye?</div>
            <div className="space-y-2">
              {lists.filter(l => l.status !== "completed").map(l => (
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
