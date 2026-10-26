"use client";
import { useLists } from "@/lib/store";

// Demodaki rozet renkleri korunur; listede olmayan zincirler API'deki rengi kullanır
const COLORS: Record<string, string> = { bim: "#dc2626", a101: "#0284c7", sok: "#ea580c", file: "#4338ca" };

export default function MarketLogo({ id, size = 32 }: { id: number | null | undefined; size?: number }) {
  const m = useLists().marketById(id);
  const color = (m && (COLORS[m.slug] || m.color)) || "#9ca3af";
  return (
    <div className="rounded-full flex items-center justify-center font-bold text-white shrink-0"
      style={{ background: color, width: size, height: size, fontSize: size * 0.42 }}>
      {m ? m.name[0] : "?"}
    </div>
  );
}
