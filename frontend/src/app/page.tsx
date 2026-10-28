"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, formatSize, num, unitPrice, Category, Deal, GroupSummary, SavingsVault, Store } from "@/lib/api";
import { useGroupIcon, useLists } from "@/lib/store";
import MarketLogo from "@/components/MarketLogo";
import ProductImage from "@/components/ProductImage";
import BarcodeScanner from "@/components/BarcodeScanner";

const cheapestOf = (g: GroupSummary) => [...g.market_prices].sort((a, b) => num(a.min_price) - num(b.min_price))[0];
const unitValue = (g: GroupSummary) => unitPrice(cheapestOf(g)?.min_price, g.quantity, g.unit)?.value ?? Infinity;

const QUICK_LINKS = [
  { href: "/lists", icon: "📋", label: "Listelerim" },
  { href: "/deals", icon: "🏷️", label: "Fırsatlar" },
  { href: "/alerts", icon: "🔔", label: "Alarmlar" },
  { href: "/stores", icon: "📍", label: "Yakınımdakiler" },
];

/** Vitrindeki yatay kaydırmalı ürün: fırsat ya da popüler ürün */
type ShowcaseItem = { groupId: number; name: string; image: string | null; categoryId: number | null;
  marketId: number | null; price: number | null; previous: number | null; badge: string | null };

/**
 * Ana sayfa sırası (Kemal'in istediği gibi): 1) arama, 2) bu ayki tasarruf, 3) hızlı erişim,
 * 4) kategoriler, 5) fırsat/popüler ürünler (yatay), 6) yakındaki marketler.
 * Arama yapılınca ya da kategori seçilince bölümler yerine sonuç listesi gösterilir.
 */
export default function HomePage() {
  const { user, categories, marketById, subcategoriesOf } = useLists();
  const groupIcon = useGroupIcon();
  const [q, setQ] = useState("");
  const [cat, setCat] = useState<number | null>(null); // null = ana sayfa bölümleri
  const [sub, setSub] = useState<number | null>(null); // kategori içinde alt kategori (null = Tümü)
  const [results, setResults] = useState<GroupSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  // "Birim fiyat": 400 g ile 1 kg'ı kilo başına fiyatla karşılaştırır
  const [byUnit, setByUnit] = useState(false);
  const [vault, setVault] = useState<SavingsVault | null>(null);
  const [showcase, setShowcase] = useState<{ title: string; items: ShowcaseItem[] } | null>(null);
  const [stores, setStores] = useState<Store[] | null>(null);

  const searching = q.trim() !== "" || cat != null;
  const subcats = useMemo(() => (cat != null && !q.trim() ? subcategoriesOf(cat) : []), [cat, q, subcategoriesOf]);
  const openCategory = (id: number | null) => { setCat(id); setSub(null); };

  useEffect(() => {
    if (!searching) { setResults(null); return; }
    let cancelled = false;
    const t = setTimeout(() => {
      // Kategori "Tümü": her alt kategorinin en temel 8 ürünü; alt kategori seçiliyse onun ürünleri
      const load = q.trim()
        ? api.searchProducts(q.trim(), cat)
        : sub == null && subcats.length
          ? Promise.all(subcats.map(s => api.searchProducts("", cat, { sort: "popular", subcategoryId: s.id, limit: 8 })))
              .then(async parts => [...parts.flat(), ...(await api.searchProducts("", cat, { sort: "popular", limit: 30 }))
                .filter(g => !subcats.some(s => s.id === g.subcategory_id))])
          : api.searchProducts("", cat, { sort: "popular", subcategoryId: sub });
      load
        .then(r => { if (!cancelled) { setResults(r); setError(null); } })
        .catch(e => { if (!cancelled) setError(e.message); });
    }, q ? 250 : 0);
    return () => { cancelled = true; clearTimeout(t); };
  }, [q, cat, sub, subcats, searching]);

  useEffect(() => {
    if (!user) { setVault(null); setStores(null); return; }
    api.savings().then(setVault).catch(() => setVault(null));
    api.myStores().then(setStores).catch(() => setStores([]));
  }, [user]);

  // Fırsat varsa fırsatlar, yoksa en çok markette/markada bulunan temel ürünler
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const deals: Deal[] = await api.deals().catch(() => []);
      if (cancelled) return;
      if (deals.length) {
        setShowcase({
          title: "🏷️ Fırsat Ürünleri",
          items: deals.slice(0, 15).map(d => ({
            groupId: d.group_id, name: d.group_name, image: d.image_url, categoryId: d.category_id,
            marketId: d.market_id, price: num(d.price), previous: num(d.previous_price), badge: "%" + d.discount_percent,
          })),
        });
        return;
      }
      const popular = await api.searchProducts("", null, { sort: "popular", limit: 15 }).catch(() => []);
      if (cancelled) return;
      setShowcase({
        title: "⭐ Popüler Ürünler",
        items: popular.map(g => {
          const c = cheapestOf(g);
          return { groupId: g.id, name: g.name, image: g.image_url, categoryId: g.category_id,
            marketId: c?.market_id ?? null, price: c ? num(c.min_price) : null, previous: null, badge: null };
        }),
      });
    })();
    return () => { cancelled = true; };
  }, [user]);

  const monthSaved = useMemo(() => {
    if (!vault) return 0;
    const now = new Date();
    return vault.records
      .filter(r => { const d = new Date(r.created_at); return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth(); })
      .reduce((s, r) => s + num(r.saved_amount), 0);
  }, [vault]);
  const monthName = new Date().toLocaleDateString("tr-TR", { month: "long" });

  return (
    <main className="p-4">
      <h1 className="text-2xl font-bold mb-4">🛒 MarketKıyas</h1>

      {/* 1) Arama */}
      <div className="flex gap-2 mb-4">
        <div className="relative flex-1">
          <input value={q} onChange={e => setQ(e.target.value)}
            placeholder="Ürün ara (örn. süt, ekmek, deterjan)"
            className="w-full pl-10 pr-4 py-3 rounded-xl bg-white border border-gray-200 focus:outline-none focus:ring-2 focus:ring-emerald-500" />
          <span className="absolute left-3 top-3.5 text-gray-400">🔍</span>
        </div>
        <button onClick={() => setScanning(true)} aria-label="Barkod okut"
          className="px-3 rounded-xl bg-white border border-gray-200 text-xs font-medium text-gray-700 flex flex-col items-center justify-center">
          <span className="text-lg leading-none">▥</span>Barkod
        </button>
      </div>
      {scanning && <BarcodeScanner onClose={() => setScanning(false)} />}

      {searching ? (
        <SearchResults
          title={q.trim() ? null : categories.find(c => c.id === cat)?.name ?? null}
          onBack={() => { setQ(""); openCategory(null); }}
          subcats={subcats} sub={sub} setSub={setSub}
          results={results} error={error} byUnit={byUnit} setByUnit={setByUnit}
          groupIcon={groupIcon} marketName={id => marketById(id)?.name} />
      ) : (
        <div className="space-y-5">
          {/* 2) Bu ayki tasarruf */}
          {user ? (
            <Link href="/profile" className="block rounded-2xl p-4 text-white bg-gradient-to-br from-emerald-600 to-teal-700 shadow-sm">
              <div className="text-xs font-semibold opacity-90 uppercase tracking-wide">Bu ayki tasarrufun · {monthName}</div>
              <div className="text-4xl font-black mt-1">{monthSaved.toFixed(2)} ₺</div>
              <div className="text-xs opacity-85 mt-1">
                Toplam: {num(vault?.total_saved).toFixed(2)} ₺ · {monthSaved > 0 ? "Böyle devam!" : "Bir liste oluşturup Fırsatçı planla başla"}
              </div>
            </Link>
          ) : (
            <Link href="/login" className="block rounded-2xl p-4 bg-emerald-50 border border-emerald-200 text-emerald-800">
              <div className="font-semibold">Tasarrufunu takip et</div>
              <div className="text-xs mt-0.5">Giriş yap, her ay ne kadar kazandığını burada gör.</div>
            </Link>
          )}

          {/* 3) Hızlı erişim */}
          <div className="grid grid-cols-4 gap-2">
            {QUICK_LINKS.map(l => (
              <Link key={l.href} href={l.href}
                className="card py-3 flex flex-col items-center justify-center text-center hover:border-emerald-200">
                <span className="text-2xl leading-none">{l.icon}</span>
                <span className="text-[11px] font-medium text-gray-700 mt-1.5 leading-tight">{l.label}</span>
              </Link>
            ))}
          </div>

          {/* 4) Kategoriler */}
          <section>
            <h2 className="font-bold text-gray-800 mb-2">Kategoriler</h2>
            <div className="grid grid-cols-4 gap-2">
              {categories.map(c => (
                <button key={c.id} onClick={() => openCategory(c.id)}
                  className="card py-3 px-1 flex flex-col items-center text-center hover:border-emerald-200">
                  <span className="text-2xl leading-none">{c.icon || "🛒"}</span>
                  <span className="text-[11px] text-gray-700 mt-1.5 leading-tight line-clamp-2">{c.name}</span>
                </button>
              ))}
            </div>
          </section>

          {/* 5) Fırsat / popüler ürünler (yatay kaydırmalı) */}
          {showcase && showcase.items.length > 0 && (
            <section>
              <div className="flex items-baseline justify-between mb-2">
                <h2 className="font-bold text-gray-800">{showcase.title}</h2>
                <Link href="/deals" className="text-xs text-emerald-700 font-medium">Tümü ›</Link>
              </div>
              <div className="flex gap-3 overflow-x-auto pb-2 -mx-4 px-4 snap-x">
                {showcase.items.map(it => (
                  <Link key={it.groupId} href={"/products/" + it.groupId}
                    className="card p-3 w-36 shrink-0 snap-start relative hover:border-emerald-200">
                    {it.badge && (
                      <span className="absolute top-2 right-2 text-[10px] font-bold bg-orange-500 text-white px-1.5 py-0.5 rounded">{it.badge}</span>
                    )}
                    <div className="flex justify-center"><ProductImage src={it.image} icon={groupIcon(it.categoryId)} size={64} /></div>
                    <div className="text-xs font-medium text-gray-800 mt-2 line-clamp-2 min-h-[2rem]">{it.name}</div>
                    {it.price != null && (
                      <div className="mt-1 flex items-center gap-1.5">
                        {it.marketId != null && <MarketLogo id={it.marketId} size={16} />}
                        <span className="font-bold text-emerald-600 text-sm">{it.price.toFixed(2)} ₺</span>
                      </div>
                    )}
                    {it.previous != null && it.previous > (it.price ?? 0) && (
                      <div className="text-[10px] text-gray-400 line-through">{it.previous.toFixed(2)} ₺</div>
                    )}
                  </Link>
                ))}
              </div>
            </section>
          )}

          {/* 6) Yakındaki marketler */}
          <section>
            <div className="flex items-baseline justify-between mb-2">
              <h2 className="font-bold text-gray-800">📍 Yakınındaki Marketler</h2>
              <Link href="/stores" className="text-xs text-emerald-700 font-medium">Düzenle ›</Link>
            </div>
            {stores && stores.length > 0 ? (
              <div className="card divide-y divide-gray-100">
                {stores.map(s => (
                  <div key={s.id} className="px-3 py-2.5 flex items-center gap-3">
                    <MarketLogo id={s.market_id} size={28} />
                    <div className="min-w-0">
                      <div className="text-sm font-medium truncate">{s.name}</div>
                      <div className="text-xs text-gray-500">{s.market_name}{s.distance_km != null ? " · " + s.distance_km.toFixed(1) + " km" : ""}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <Link href={user ? "/stores" : "/login"} className="card p-4 block text-sm text-gray-600 hover:border-emerald-200">
                Fiyatların senin şubelerine göre hesaplanması için yakınındaki marketleri seç ›
              </Link>
            )}
          </section>
        </div>
      )}
    </main>
  );
}

// Alt kategori şeridindeki simgeler; eşleşmezse üst kategorinin simgesi
const SUB_ICONS: [RegExp, string][] = [
  [/peynir/i, "🧀"], [/yo[gğ]urt|ayran|kefir/i, "🥛"], [/s[uü]t/i, "🥛"], [/yumurta/i, "🥚"], [/zeytin/i, "🫒"],
  [/bal|re[cç]el|pekmez|helva|tahin/i, "🍯"], [/tereya[gğ]|margarin/i, "🧈"], [/gevrek|granola/i, "🥣"],
  [/ekmek|unlu/i, "🍞"], [/[cç]ay/i, "🍵"], [/kahve/i, "☕"], [/su$|maden/i, "💧"], [/meyve suyu|nektar/i, "🧃"],
  [/gazl|kola/i, "🥤"], [/[cç]ikolata/i, "🍫"], [/bisk[uü]vi|kraker|kek|gofret/i, "🍪"], [/cips|kuruyemi/i, "🥜"],
  [/dondurma/i, "🍦"], [/[sş]eker/i, "🍬"], [/k[iı]rm[iı]z[iı] et|sakatat/i, "🥩"], [/beyaz et|tavuk/i, "🍗"],
  [/deniz|bal[iı]k/i, "🐟"], [/[sş]ark[uü]teri|sucuk|salam/i, "🌭"], [/meyve/i, "🍎"], [/sebze/i, "🥕"],
  [/makarna|eri[sş]te/i, "🍝"], [/bakliyat|pirin[cç]|bulgur/i, "🌾"], [/ya[gğ]/i, "🫗"], [/sal[cç]a|sos|ket[cç]ap/i, "🥫"],
  [/baharat|tuz/i, "🧂"], [/deterjan|temizle|bula[sş][iı]k|[cç]ama[sş][iı]r/i, "🧴"], [/ka[gğ][iı]t|pe[cç]ete|havlu/i, "🧻"],
  [/sa[cç]|[sş]ampuan/i, "💇"], [/a[gğ][iı]z|di[sş]/i, "🪥"], [/bebek|mama|bez/i, "🍼"], [/hijyen|ped/i, "🩹"],
];
const subIcon = (name: string, fallback: string) => SUB_ICONS.find(([re]) => re.test(name))?.[1] ?? fallback;

function SearchResults({
  title, onBack, results, error, byUnit, setByUnit, groupIcon, marketName, subcats = [], sub = null, setSub,
}: {
  title: string | null; onBack: () => void; results: GroupSummary[] | null; error: string | null;
  byUnit: boolean; setByUnit: (f: (v: boolean) => boolean) => void;
  groupIcon: (categoryId: number | null | undefined) => string; marketName: (id: number) => string | undefined;
  // Kategori ekranında alt kategori şeridi: Tümü / Süt / Peynir / Zeytin…
  subcats?: Category[]; sub?: number | null; setSub?: (id: number | null) => void;
}) {
  const sorted = byUnit && results ? [...results].sort((a, b) => unitValue(a) - unitValue(b)) : results || [];
  // "Tümü"de ürünler alt kategori başlıkları altında; alt kategorisi bilinmeyenler en sonda "Diğer"
  const sections = subcats.length && sub == null
    ? [...subcats.map(s => ({ key: String(s.id), subId: s.id as number | null, title: s.name, icon: subIcon(s.name, s.icon || ""), groups: sorted.filter(g => g.subcategory_id === s.id) })),
       { key: "other", subId: null as number | null, title: "Diğer", icon: "", groups: sorted.filter(g => !subcats.some(s => s.id === g.subcategory_id)) }]
        .filter(s => s.groups.length)
    : [{ key: "all", subId: null as number | null, title: null as string | null, icon: "", groups: sorted }];
  const row = (group: GroupSummary) => <ProductRow key={group.id} group={group} groupIcon={groupIcon} marketName={marketName} />;
  return (
    <>
      <div className="flex items-center justify-between mb-2">
        <button onClick={onBack} className="text-sm text-gray-600">← Ana sayfa</button>
        {(results?.length ?? 0) > 1 && (
          <button onClick={() => setByUnit(v => !v)}
            className={"text-xs px-2.5 py-1 rounded-full border " + (byUnit ? "bg-emerald-50 border-emerald-300 text-emerald-700" : "bg-white border-gray-200 text-gray-600")}>
            {byUnit ? "✓ " : ""}Kilo/litre fiyatına göre sırala
          </button>
        )}
      </div>
      {title && <h2 className="font-bold text-gray-800 mb-2">{title}</h2>}
      {subcats.length > 0 && setSub && (
        <div className="flex gap-2 overflow-x-auto pb-2 -mx-4 px-4 mb-2 sticky top-0 z-10 bg-gray-50 pt-1">
          {[{ id: null as number | null, name: "Tümü", icon: "▦" }, ...subcats.map(s => ({ id: s.id as number | null, name: s.name, icon: subIcon(s.name, s.icon || "🛒") }))].map(c => (
            <button key={c.id ?? "all"} onClick={() => setSub(c.id)}
              className={"whitespace-nowrap flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-xl border shadow-sm " + (sub === c.id
                ? "bg-emerald-700 text-white border-emerald-700 font-semibold"
                : "bg-white text-gray-700 border-gray-200")}>
              <span>{c.icon}</span>{c.name}
            </button>
          ))}
        </div>
      )}
      {error && <div className="card p-4 text-sm text-red-600 mb-3">Ürünler yüklenemedi: {error}</div>}
      <div className="space-y-3">
        {sections.map(s => s.title ? (
          <section key={s.key} className="space-y-3">
            <div className="flex items-baseline justify-between pt-2">
              <h3 className="text-sm font-bold text-gray-600">{s.icon} {s.title}</h3>
              {s.subId != null && setSub && (
                <button onClick={() => setSub(s.subId)} className="text-xs text-emerald-700 font-medium">Tümünü gör ›</button>
              )}
            </div>
            {s.groups.map(row)}
          </section>
        ) : s.groups.map(row))}
        {results === null && !error && <div className="text-center text-gray-400 py-12">Yükleniyor…</div>}
        {results?.length === 0 && (
          <div className="text-center text-gray-500 py-12">
            <div className="text-4xl mb-2">🔍</div>
            <div>Sonuç bulunamadı</div>
          </div>
        )}
      </div>
    </>
  );
}

function ProductRow({
  group, groupIcon, marketName,
}: {
  group: GroupSummary; groupIcon: (categoryId: number | null | undefined) => string; marketName: (id: number) => string | undefined;
}) {
          const cheapest = cheapestOf(group);
          const perUnit = cheapest && unitPrice(cheapest.min_price, group.quantity, group.unit);
          return (
            <Link href={"/products/" + group.id}
              className="card p-4 block hover:border-emerald-200">
              <div className="flex items-start gap-3">
                <ProductImage src={group.image_url} icon={groupIcon(group.category_id)} size={48} />
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900">{group.name}</div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {[formatSize(group.quantity, group.unit), group.market_prices.length + " market"].filter(Boolean).join(" · ")}
                  </div>
                  {cheapest && (
                    <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-sm">
                      <MarketLogo id={cheapest.market_id} size={20} />
                      <span className="text-gray-600">{marketName(cheapest.market_id)}</span>
                      <span className="font-bold text-emerald-600 whitespace-nowrap">{num(cheapest.min_price).toFixed(2)} ₺</span>
                      {perUnit && <span className="text-xs text-gray-400 whitespace-nowrap">({perUnit.label})</span>}
                      {cheapest.regular_price && (
                        <span className="text-xs bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded">PROMO</span>
                      )}
                    </div>
                  )}
                </div>
                <div className="text-gray-300">›</div>
              </div>
            </Link>
          );
}
