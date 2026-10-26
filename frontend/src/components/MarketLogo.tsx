"use client";
import { useState } from "react";
import { useLists } from "@/lib/store";

// Demodaki rozet renkleri korunur; diğer zincirlerin kurumsal renkleri, listede olmayanlar API'deki rengi kullanır
const COLORS: Record<string, string> = {
  bim: "#dc2626", a101: "#0284c7", sok: "#ea580c", file: "#4338ca",
  migros: "#f97316", carrefour: "#1e40af", tarim_kredi: "#16a34a", hakmar: "#b91c1c",
};
// Rozette yazan kısa ad
const LABELS: Record<string, string> = {
  bim: "BİM", a101: "A101", sok: "ŞOK", file: "File", migros: "M", carrefour: "CSA", tarim_kredi: "TK", hakmar: "H",
};

export default function MarketLogo({ id, size = 32 }: { id: number | null | undefined; size?: number }) {
  const m = useLists().marketById(id);
  const [logoFailed, setLogoFailed] = useState(false);
  if (m?.logo_url && !logoFailed) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img src={m.logo_url} alt={m.name} onError={() => setLogoFailed(true)}
        className="rounded-full object-contain bg-white shrink-0" style={{ width: size, height: size }} />
    );
  }
  const color = (m && (COLORS[m.slug] || m.color)) || "#9ca3af";
  const label = m ? LABELS[m.slug] || m.name[0] : "?";
  return (
    <div className="rounded-full flex items-center justify-center font-bold text-white shrink-0 leading-none"
      title={m?.name}
      style={{ background: color, width: size, height: size, fontSize: size * (label.length > 2 ? 0.3 : 0.42) }}>
      {label}
    </div>
  );
}
