"use client";
import { useEffect, useState } from "react";
import { api, Store } from "@/lib/api";
import { useLists } from "@/lib/store";
import MarketLogo from "@/components/MarketLogo";

// "Çevremdeki marketler": seçilen şubeler varsa tüm fiyatlar yalnızca bu şubelerden gelir
export default function StoresPage() {
  const { user, setToast, refreshLists } = useLists();
  const [stores, setStores] = useState<Store[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [status, setStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!user) return;
    api.myStores().then(mine => {
      setStores(mine);
      setSelected(new Set(mine.map(s => s.id)));
    }).catch(() => {});
  }, [user]);

  const findNearby = () => {
    if (!navigator.geolocation) { setStatus("Tarayıcınız konum paylaşımını desteklemiyor."); return; }
    setStatus("Konumunuz alınıyor…");
    navigator.geolocation.getCurrentPosition(async pos => {
      setStatus("Yakındaki marketler aranıyor…");
      try {
        const nearby = await api.nearbyStores(pos.coords.latitude, pos.coords.longitude);
        const byId = new Map(stores.filter(s => selected.has(s.id)).map(s => [s.id, s]));
        nearby.forEach(s => byId.set(s.id, s));
        setStores(Array.from(byId.values()));
        setStatus(nearby.length ? null : "Yakında market bulunamadı.");
      } catch (e) { setStatus((e as Error).message); }
    }, () => setStatus("Konum izni verilmedi."));
  };

  const toggle = (id: number) => setSelected(prev => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });

  const save = async () => {
    setSaving(true);
    try {
      await api.selectStores(Array.from(selected));
      await refreshLists();
      setToast("Marketleriniz kaydedildi");
    } catch (e) { setToast((e as Error).message); }
    finally { setSaving(false); }
  };

  if (!user) return <div className="p-6">Yükleniyor…</div>;

  return (
    <main className="p-4">
      <h1 className="text-2xl font-bold mb-1">📍 Marketlerim</h1>
      <p className="text-sm text-gray-500 mb-4">
        Alışveriş yaptığınız şubeleri seçin; fiyatlar ve planlar yalnızca bu şubelere göre hesaplanır.
        Hiç seçmezseniz zincirlerin genel fiyatları kullanılır.
      </p>
      <button onClick={findNearby} className="w-full bg-white border border-emerald-600 text-emerald-700 py-3 rounded-xl font-semibold mb-3">
        📡 Yakınımdaki marketleri bul
      </button>
      {status && <div className="text-sm text-gray-500 text-center mb-3">{status}</div>}
      <div className="card divide-y divide-gray-100 mb-4">
        {stores.map(s => (
          <label key={s.id} className="px-4 py-3 flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={selected.has(s.id)} onChange={() => toggle(s.id)} className="w-5 h-5 accent-emerald-600" />
            <MarketLogo id={s.market_id} size={28} />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{s.name}</div>
              <div className="text-xs text-gray-500">
                {s.market_name}{s.distance_km != null && " · " + s.distance_km.toFixed(1) + " km"}
              </div>
            </div>
          </label>
        ))}
        {stores.length === 0 && <div className="px-4 py-6 text-center text-sm text-gray-400">Henüz şube seçmediniz.</div>}
      </div>
      <button onClick={save} disabled={saving} className="w-full bg-emerald-600 disabled:opacity-60 text-white py-3 rounded-xl font-semibold">
        {saving ? "Kaydediliyor…" : "Kaydet (" + selected.size + " şube)"}
      </button>
    </main>
  );
}
