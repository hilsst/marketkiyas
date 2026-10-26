"use client";
import { useLists } from "@/lib/store";
import { MARKET_MAP } from "@/lib/demo-data";

export default function ProfilePage() {
  const { savings } = useLists();

  const totalSavings = savings.reduce((s, x) => s + x.amount, 0);

  return (
    <main className="p-4">
      <h1 className="text-2xl font-bold mb-4">👤 Profil</h1>
      
      <div className="card p-4 space-y-3 mb-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-emerald-600 text-white flex items-center justify-center text-xl font-bold">D</div>
          <div>
            <div className="font-semibold">Demo Kullanıcı</div>
            <div className="text-xs text-gray-500">demo@marketkiyas.app</div>
          </div>
        </div>
        <hr />
        <div className="text-sm text-gray-600">📊 Veri son güncelleme: bugün 03:00</div>
        <div className="text-sm text-gray-600">📍 Bildirimler: açık</div>
        <div className="text-xs text-gray-400 pt-2 border-t">
          ℹ️ Bilgilendirme amaçlıdır. Mağaza fiyatı değişebilir.
        </div>
      </div>

      {/* Tasarruf Kasası */}
      <div className="card p-4 bg-gradient-to-br from-emerald-600 to-teal-700 text-white border-none shadow-md">
        <div className="text-xs font-semibold opacity-80 uppercase tracking-wider">Toplam Tasarruf</div>
        <div className="text-4xl font-black mt-1">{totalSavings.toFixed(2)} ₺</div>
        <div className="text-xs mt-2 opacity-90 bg-black/10 p-2 rounded-lg">
          Fırsatçı kombinasyonları kullanarak bugüne kadar biriktirdiğiniz tutar.
        </div>
      </div>

      <div className="mt-6">
        <h2 className="text-sm font-bold text-gray-700 mb-3">Tasarruf Geçmişi</h2>
        {savings.length === 0 ? (
          <div className="text-center text-gray-400 text-sm py-8">
            Henüz tamamlanmış bir tasarruflu alışverişiniz yok.
          </div>
        ) : (
          <div className="space-y-2">
            {savings.map(s => (
              <div key={s.id} className="card p-3 flex justify-between items-center">
                <div>
                  <div className="font-semibold text-sm">{s.listName}</div>
                  <div className="text-xs text-gray-500">{new Date(s.date).toLocaleDateString("tr-TR")} · {s.itemCount} ürün</div>
                </div>
                <div className="font-bold text-emerald-600">+{s.amount.toFixed(2)} ₺</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
