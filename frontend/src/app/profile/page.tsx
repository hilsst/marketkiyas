"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, num, SavingsVault } from "@/lib/api";
import { useLists } from "@/lib/store";

export default function ProfilePage() {
  const { user, logout } = useLists();
  const [vault, setVault] = useState<SavingsVault | null>(null);
  const [storeCount, setStoreCount] = useState<number | null>(null);

  useEffect(() => {
    if (!user) return;
    api.savings().then(setVault).catch(() => {});
    api.myStores().then(s => setStoreCount(s.length)).catch(() => {});
  }, [user]);

  if (!user) return <div className="p-6">Yükleniyor…</div>;

  const displayName = user.full_name || user.email.split("@")[0];
  const records = vault?.records || [];

  return (
    <main className="p-4">
      <h1 className="text-2xl font-bold mb-4">👤 Profil</h1>

      <div className="card p-4 space-y-3 mb-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-emerald-600 text-white flex items-center justify-center text-xl font-bold">
            {displayName[0].toLocaleUpperCase("tr-TR")}
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-semibold">{displayName}</div>
            <div className="text-xs text-gray-500 truncate">{user.email}</div>
          </div>
          <button onClick={logout} className="text-xs text-gray-500 underline">Çıkış</button>
        </div>
        <hr />
        <Link href="/stores" className="flex justify-between text-sm text-gray-600">
          <span>📍 Marketlerim: {storeCount ? storeCount + " şube seçili" : "seçilmedi (tüm Türkiye fiyatları)"}</span>
          <span className="text-gray-300">›</span>
        </Link>
        <div className="text-sm text-gray-600">📍 Bildirimler: açık</div>
        <div className="text-xs text-gray-400 pt-2 border-t">
          ℹ️ Bilgilendirme amaçlıdır. Mağaza fiyatı değişebilir.
        </div>
      </div>

      {/* Tasarruf Kasası */}
      <div className="card p-4 bg-gradient-to-br from-emerald-600 to-teal-700 text-white border-none shadow-md">
        <div className="text-xs font-semibold opacity-80 uppercase tracking-wider">Toplam Tasarruf</div>
        <div className="text-4xl font-black mt-1">{num(vault?.total_saved).toFixed(2)} ₺</div>
        <div className="text-xs mt-2 opacity-90 bg-black/10 p-2 rounded-lg">
          Fırsatçı kombinasyonları kullanarak bugüne kadar biriktirdiğiniz tutar.
        </div>
      </div>

      <div className="mt-6">
        <h2 className="text-sm font-bold text-gray-700 mb-3">Tasarruf Geçmişi</h2>
        {records.length === 0 ? (
          <div className="text-center text-gray-400 text-sm py-8">
            Henüz tamamlanmış bir tasarruflu alışverişiniz yok.
          </div>
        ) : (
          <div className="space-y-2">
            {records.map(s => (
              <div key={s.id} className="card p-3 flex justify-between items-center">
                <div>
                  <div className="font-semibold text-sm">{s.list_name}</div>
                  <div className="text-xs text-gray-500">{new Date(s.created_at).toLocaleDateString("tr-TR")} · {s.item_count} ürün</div>
                </div>
                <div className="font-bold text-emerald-600">+{num(s.saved_amount).toFixed(2)} ₺</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
