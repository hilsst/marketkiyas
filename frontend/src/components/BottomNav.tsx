"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLists } from "@/lib/store";
const TABS = [
  { href: "/",        label: "Ana Sayfa", icon: "🏠" },
  { href: "/deals",   label: "Fırsatlar", icon: "🏷️" },
  { href: "/lists",   label: "Listeler",  icon: "📋" },
  { href: "/alerts",  label: "Alarmlar",  icon: "🔔" },
  { href: "/profile", label: "Profil",    icon: "👤" },
];
export default function BottomNav() {
  const p = usePathname();
  const { unreadAlerts } = useLists();
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-40">
      <div className="max-w-md mx-auto grid grid-cols-5">
        {TABS.map(t => {
          const active = t.href === "/" ? p === "/" : p.startsWith(t.href);
          const badge = t.href === "/alerts" && unreadAlerts > 0 ? unreadAlerts : 0;
          return (
            <Link key={t.href} href={t.href}
              className={"relative flex flex-col items-center py-2 " +
                (active ? "text-emerald-600" : "text-gray-500")}>
              <span className="text-xl">{t.icon}</span>
              <span className="text-[11px] mt-0.5">{t.label}</span>
              {badge > 0 && (
                <span className="absolute top-1 left-1/2 ml-2 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center">
                  {badge}
                </span>
              )}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
