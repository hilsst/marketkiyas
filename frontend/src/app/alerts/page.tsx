"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, formatSize, num, PriceAlert } from "@/lib/api";
import { useGroupIcon, useLists } from "@/lib/store";
import MarketLogo from "@/components/MarketLogo";
import ProductImage from "@/components/ProductImage";

export default function AlertsPage() {
  const { hydrated, user, marketById, refreshAlerts, setToast } = useLists();
  const groupIcon = useGroupIcon();
  const [alerts, setAlerts] = useState<PriceAlert[] | null>(null);

  useEffect(() => {
    if (!user) return;
    // Sayfa açılınca düşen fiyatlar "görüldü" sayılır; vurgular bu ziyaret boyunca kalır
    api.alerts()
      .then(a => { setAlerts(a); return api.markAlertsSeen(); })
      .then(refreshAlerts)
      .catch(e => { setAlerts([]); setToast((e as Error).message); });
  }, [user, refreshAlerts, setToast]);

  if (!hydrated || !user) return <div className="p-6">Yükleniyor…</div>;

  const remove = async (id: number) => {
    try {
      await api.deleteAlert(id);
      setAlerts(a => (a || []).filter(x => x.id !== id));
    } catch (e) { setToast((e as Error).message); }
  };

  const dropped = (alerts || []).filter(a => a.triggered);
  const waiting = (alerts || []).filter(a => !a.triggered);

  const row = (a: PriceAlert) => {
    const before = num(a.target_price ?? a.baseline_price);
    const now = a.current_price == null ? null : num(a.current_price);
    return (
      <div key={a.id} className={"card p-3 flex items-center gap-3 " + (a.unread ? "border-emerald-300 bg-emerald-50/60" : "")}>
        <Link href={"/products/" + a.group_id} className="flex items-center gap-3 flex-1 min-w-0">
          <ProductImage src={a.image_url} icon={groupIcon(a.category_id)} size={44} />
          <div className="min-w-0">
            <div className="font-semibold text-sm truncate">{a.group_name}</div>
            <div className="text-xs text-gray-500">
              {a.target_price ? "Hedef: " + num(a.target_price).toFixed(2) + " ₺ altı" : "Kurulduğunda: " + before.toFixed(2) + " ₺"}
              {formatSize(a.quantity, a.unit) && " · " + formatSize(a.quantity, a.unit)}
            </div>
            {now != null && (
              <div className="text-xs mt-0.5 flex items-center gap-1.5">
                {a.current_market_id != null && <MarketLogo id={a.current_market_id} size={16} />}
                <span className={a.triggered ? "font-bold text-emerald-700" : "text-gray-700"}>Şu an {now.toFixed(2)} ₺</span>
                {a.triggered && before > now && (
                  <span className="bg-emerald-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">
                    {(before - now).toFixed(2)} ₺ düştü
                  </span>
                )}
                {a.current_market_id != null && <span className="text-gray-400">{marketById(a.current_market_id)?.name}</span>}
              </div>
            )}
            {now == null && <div className="text-xs text-gray-400 mt-0.5">Seçtiğiniz marketlerde şu an yok</div>}
          </div>
        </Link>
        <button onClick={() => remove(a.id)} aria-label="Alarmı kaldır" className="text-gray-300 hover:text-red-500 text-lg px-1">✕</button>
      </div>
    );
  };

  return (
    <main className="p-4">
      <h1 className="text-2xl font-bold mb-1">🔔 Fiyat Alarmları</h1>
      <p className="text-xs text-gray-500 mb-4">Takip ettiğiniz ürünlerin fiyatı düşünce burada görünür.</p>
      {alerts === null && <div className="text-center text-gray-400 py-8">Yükleniyor…</div>}
      {alerts?.length === 0 && (
        <div className="card p-6 text-center text-gray-500">
          <div className="text-3xl mb-2">🔕</div>
          <div className="text-sm">Henüz alarm yok</div>
          <div className="text-xs mt-1">Bir ürünün sayfasında 🔔 düğmesine dokunun</div>
        </div>
      )}
      {dropped.length > 0 && (
        <>
          <div className="text-xs font-semibold text-emerald-700 mb-2">FİYATI DÜŞENLER</div>
          <div className="space-y-2 mb-5">{dropped.map(row)}</div>
        </>
      )}
      {waiting.length > 0 && (
        <>
          <div className="text-xs font-semibold text-gray-500 mb-2">TAKİPTE</div>
          <div className="space-y-2">{waiting.map(row)}</div>
        </>
      )}
    </main>
  );
}
