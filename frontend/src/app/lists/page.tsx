"use client";
import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, num } from "@/lib/api";
import { useLists } from "@/lib/store";
import MarketLogo from "@/components/MarketLogo";

export default function ListsPage() {
  const router = useRouter();
  const { lists, createList, hydrated, user, marketById, setToast, refreshLists } = useLists();
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [joining, setJoining] = useState(false);
  const [code, setCode] = useState("");

  if (!hydrated || !user) return <div className="p-6">Yükleniyor…</div>;

  const save = async () => {
    if (!name.trim()) return;
    try {
      const id = await createList(name.trim());
      setName(""); setCreating(false);
      router.push("/lists/" + id); // yeni liste hemen açılsın
    } catch (e) { setToast((e as Error).message); }
  };

  const join = async () => {
    if (!code.trim()) return;
    try {
      const joined = await api.joinList(code.trim());
      await refreshLists();
      setCode(""); setJoining(false);
      router.push("/lists/" + joined.id);
    } catch (e) { setToast((e as Error).message); }
  };

  return (
    <main className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">📋 Listeler</h1>
        <div className="flex gap-2">
          <button onClick={() => { setJoining(true); setCreating(false); }} className="bg-white border border-gray-200 text-gray-700 text-sm px-3 py-1.5 rounded-lg">👥 Kodla Katıl</button>
          <button onClick={() => { setCreating(true); setJoining(false); }} className="bg-emerald-600 text-white text-sm px-3 py-1.5 rounded-lg">+ Yeni</button>
        </div>
      </div>
      {joining && (
        <div className="card p-3 mb-3">
          <div className="text-xs text-gray-500 mb-2">Eşinizin ya da ev arkadaşınızın paylaştığı 8 haneli kodu yazın.</div>
          <input value={code} onChange={e => setCode(e.target.value.toUpperCase())} placeholder="Davet kodu (örn. K7PX2M9Q)"
            className="w-full border rounded-lg px-3 py-2 mb-2 tracking-widest font-mono" />
          <div className="flex gap-2">
            <button onClick={join} className="flex-1 bg-emerald-600 text-white py-2 rounded-lg">Listeye Katıl</button>
            <button onClick={() => { setJoining(false); setCode(""); }} className="px-4 bg-gray-100 rounded-lg">İptal</button>
          </div>
        </div>
      )}
      {creating && (
        <div className="card p-3 mb-3">
          <input value={name} onChange={e => setName(e.target.value)} placeholder="Liste adı"
            className="w-full border rounded-lg px-3 py-2 mb-2" />
          <div className="flex gap-2">
            <button onClick={save} className="flex-1 bg-emerald-600 text-white py-2 rounded-lg">Kaydet</button>
            <button onClick={() => { setCreating(false); setName(""); }} className="px-4 bg-gray-100 rounded-lg">İptal</button>
          </div>
        </div>
      )}
      <div className="space-y-3">
        {lists.map(l => (
          <Link key={l.id} href={"/lists/" + l.id} className="card p-4 block hover:border-emerald-200">
            <div className="flex items-center justify-between">
              <div className="font-semibold flex items-center gap-2">
                {l.name}
                {(l.member_count > 0 || l.owner_id !== user.id) && (
                  <span className="text-[10px] font-semibold bg-sky-100 text-sky-700 px-1.5 py-0.5 rounded">
                    👥 {l.owner_id === user.id ? "Ortak" : l.owner_name + " ile"}
                  </span>
                )}
              </div>
              <div className="text-xs text-gray-400">{l.item_count} ürün</div>
            </div>
            <div className="text-sm text-gray-500 mt-1">
              Tahmini: <b className="text-gray-900">{num(l.estimated_total).toFixed(2)} ₺</b>
            </div>
            {l.top_market_id != null && (
              <div className="mt-2 flex items-center gap-2 text-xs">
                <MarketLogo id={l.top_market_id} size={18} />
                <span className="text-gray-600">En çok: {marketById(l.top_market_id)?.name}</span>
              </div>
            )}
          </Link>
        ))}
        {lists.length === 0 && !creating && (
          <div className="text-center text-gray-400 text-sm py-8">Henüz listeniz yok. “+ Yeni” ile oluşturun.</div>
        )}
      </div>
    </main>
  );
}
