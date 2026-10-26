import { MARKET_MAP, MarketSlug } from "@/lib/demo-data";
export default function MarketLogo({ slug, size = 32 }:
  { slug: MarketSlug; size?: number }) {
  const m = MARKET_MAP[slug];
  return (
    <div className="rounded-full flex items-center justify-center font-bold text-white shrink-0"
      style={{ background: m.color, width: size, height: size, fontSize: size * 0.42 }}>
      {m.name[0]}
    </div>
  );
}
