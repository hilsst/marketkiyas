"use client";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, num, GroupSummary, ListDetail } from "@/lib/api";
import { useGroupIcon, useLists } from "@/lib/store";
import { rememberGroup } from "@/lib/recent";
import ItemTile from "@/components/ItemTile";
import ItemSheet from "@/components/ItemSheet";

/** Bring! tarzı ürün ekleme: kategori kutuları, dokun ekle / tekrar dokun çıkar, basılı tut: marka ve adet. */
export default function AddItemsPage() {
  const { id } = useParams();
  const listId = Number(id);
  const router = useRouter();
  const { hydrated, user, categories, categoryById, refreshLists, setToast } = useLists();
  const groupIcon = useGroupIcon();
  const [detail, setDetail] = useState<ListDetail | null>(null);
  const [q, setQ] = useState("");
  const [cat, setCat] = useState<number | null>(null);
  const [results, setResults] = useState<GroupSummary[] | null>(null);
  const [sheetGroupId, setSheetGroupId] = useState<number | null>(null);
  const busy = useRef(new Set<number>());

  useEffect(() => {
    if (user) api.list(listId).then(setDetail).catch(() => router.replace("/lists"));
  }, [user, listId, router]);

  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(() => {
      // Arama yokken "Tümü": her kategoriden en temel 12 ürün; kategori seçiliyse o kategorinin temel ürünleri
      const load = q.trim()
        ? api.searchProducts(q.trim(), cat)
        : cat != null
          ? api.searchProducts("", cat, { sort: "popular" })
          : Promise.all(categories.map(c => api.searchProducts("", c.id, { sort: "popular", limit: 12 }))).then(r => r.flat());
      load
        .then(r => { if (!cancelled) setResults(r); })
        .catch(e => { if (!cancelled) { setResults([]); setToast(e.message); } });
    }, q ? 250 : 0);
    return () => { cancelled = true; clearTimeout(t); };
  }, [q, cat, categories, setToast]);

  const itemByGroup = useMemo(() => new Map((detail?.items || []).map(i => [i.group_id, i])), [detail]);

  // Arama yoksa kutular kategori kategori; aramada tek bölüm
  const sections = useMemo(() => {
    if (!results) return [];
    if (q.trim()) return [{ title: "ARAMA: \"" + q.trim() + "\"", groups: results }];
    const by = new Map<number | null, GroupSummary[]>();
    for (const g of results) by.set(g.category_id, [...(by.get(g.category_id) || []), g]);
    return Array.from(by.entries())
      .sort(([a], [b]) => (a == null ? 1 : b == null ? -1 : categories.findIndex(c => c.id === a) - categories.findIndex(c => c.id === b)))
      .map(([cid, groups]) => ({ title: (categoryById(cid)?.name || "Diğer").toLocaleUpperCase("tr"), groups }));
  }, [results, q, categories, categoryById]);

  const run = async (groupId: number, call: () => Promise<ListDetail>) => {
    if (busy.current.has(groupId)) return;
    busy.current.add(groupId);
    try { setDetail(await call()); } catch (e) { setToast((e as Error).message); }
    finally { busy.current.delete(groupId); }
  };

  const toggle = (g: GroupSummary) => {
    const item = itemByGroup.get(g.id);
    if (item) {
      rememberGroup({ group_id: g.id, name: g.name, category_id: g.category_id });
      return run(g.id, () => api.removeItem(listId, item.id));
    }
    return run(g.id, () => api.addItem(listId, g.id));
  };

  const close = () => { refreshLists(); router.push("/lists/" + listId); };

  if (!hydrated || !user || !detail) return <div className="p-6">Yükleniyor…</div>;

  const sheetGroup = results?.find(g => g.id === sheetGroupId);
  const sheetItem = sheetGroupId != null ? itemByGroup.get(sheetGroupId) : undefined;
  const chip = (active: boolean) =>
    "whitespace-nowrap px-3 py-1.5 rounded-full text-xs " + (active ? "bg-emerald-600 text-white" : "bg-gray-100 text-gray-700");

  return (
    <main className="pb-6">
      <div className="bg-white px-4 pt-4 pb-3 border-b border-gray-100 sticky top-0 z-20">
        <div className="flex justify-between items-center">
          <button onClick={close} className="text-gray-500 text-sm">✕ Kapat</button>
          <span className="font-bold">Ürün Ekle</span>
          <button onClick={close} className="text-emerald-600 text-sm font-bold">Bitti ({detail.items.length})</button>
        </div>
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="🔍  Ne lazım? (örn. süt)"
          className="mt-3 w-full bg-gray-100 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500" />
        <div className="flex gap-2 mt-3 overflow-x-auto -mx-4 px-4">
          <button onClick={() => setCat(null)} className={chip(cat == null)}>Tümü</button>
          {categories.map(c => (
            <button key={c.id} onClick={() => setCat(c.id)} className={chip(cat === c.id)}>{c.icon} {c.name}</button>
          ))}
        </div>
      </div>

      <div className="px-4">
        {results === null && <div className="text-center text-gray-400 py-12">Yükleniyor…</div>}
        {results?.length === 0 && (
          <div className="text-center text-gray-500 py-12 text-sm">
            <div className="text-3xl mb-2">🔍</div>
            Bulunamadı. Ana sayfadaki Barkod düğmesiyle de arayabilirsiniz.
          </div>
        )}
        {sections.map(s => (
          <div key={s.title}>
            <div className="text-xs font-bold text-gray-500 tracking-wide mt-4 mb-2">{s.title}</div>
            <div className="grid grid-cols-4 gap-2">
              {s.groups.map(g => {
                const item = itemByGroup.get(g.id);
                return (
                  <ItemTile key={g.id} small icon={groupIcon(g.category_id)} image={g.image_url} name={g.name}
                    variant={item ? "on" : "off"} qty={item ? num(item.quantity) : undefined}
                    locked={item?.preferred_brand != null}
                    sub={g.min_price != null ? num(g.min_price).toFixed(2) + " ₺" : null}
                    onClick={() => toggle(g)} onLongPress={() => setSheetGroupId(g.id)} />
                );
              })}
            </div>
          </div>
        ))}
        {results && results.length > 0 && (
          <div className="mt-4 text-center text-[11px] text-gray-400">Dokun: ekle · tekrar dokun: çıkar · basılı tut: marka/adet</div>
        )}
      </div>

      {sheetGroup && (
        <ItemSheet groupId={sheetGroup.id} icon={groupIcon(sheetGroup.category_id)} item={sheetItem}
          onClose={() => setSheetGroupId(null)}
          onPatch={sheetItem ? patch => run(sheetGroup.id, () => api.updateItem(listId, sheetItem.id, patch)) : undefined}
          onRemove={sheetItem ? () => { setSheetGroupId(null); toggle(sheetGroup); } : undefined}
          onAdd={sheetItem ? undefined : () => { toggle(sheetGroup); }} />
      )}
    </main>
  );
}
