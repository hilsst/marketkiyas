"use client";
import { useRef } from "react";

export type TileVariant = "on" | "off" | "done" | "shared";

const VARIANTS: Record<TileVariant, string> = {
  on: "bg-emerald-600 text-white shadow-[0_2px_6px_#05966955]",
  shared: "bg-sky-500 text-white shadow-[0_2px_6px_#0ea5e955]",
  off: "bg-white text-gray-700 border border-gray-200",
  done: "bg-gray-200 text-gray-400",
};

/** Bring! tarzı kare ürün kutusu. Dokunma: onClick; basılı tutma (0,45 sn): onLongPress. */
export default function ItemTile({
  icon, name, sub, qty, locked, variant = "on", small, onClick, onLongPress,
}: {
  icon: string; name: string; sub?: string | null; qty?: number; locked?: boolean;
  variant?: TileVariant; small?: boolean; onClick?: () => void; onLongPress?: () => void;
}) {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const longPressed = useRef(false);
  const start = () => {
    longPressed.current = false;
    if (!onLongPress) return;
    timer.current = setTimeout(() => { longPressed.current = true; onLongPress(); }, 450);
  };
  const cancel = () => { if (timer.current) clearTimeout(timer.current); timer.current = null; };

  return (
    <button type="button"
      onPointerDown={start} onPointerUp={cancel} onPointerLeave={cancel} onPointerCancel={cancel}
      onContextMenu={e => { if (onLongPress) e.preventDefault(); }}
      onClick={() => { if (!longPressed.current) onClick?.(); }}
      className={"relative aspect-square rounded-2xl flex flex-col items-center justify-center text-center p-1 select-none " +
        "active:scale-95 transition-transform " + VARIANTS[variant]}>
      {qty != null && qty > 1 && (
        <span className={"absolute top-1.5 right-1.5 min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-extrabold flex items-center justify-center " +
          (variant === "off" || variant === "done" ? "bg-emerald-600 text-white" : "bg-white text-emerald-700")}>
          {qty}
        </span>
      )}
      {locked && <span className="absolute top-1.5 left-2 text-[10px]">🔒</span>}
      <span className={(small ? "text-2xl" : "text-3xl") + " leading-none " + (variant === "done" ? "opacity-50" : "")}>{icon}</span>
      <span className={"font-semibold leading-tight mt-1 line-clamp-2 " + (small ? "text-[11px]" : "text-xs") + (variant === "done" ? " line-through" : "")}>
        {name}
      </span>
      {sub && <span className="text-[10px] opacity-85 mt-0.5 leading-tight line-clamp-1">{sub}</span>}
    </button>
  );
}
