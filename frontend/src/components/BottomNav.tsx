"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
const TABS = [
  { href: "/",        label: "Ara",      icon: "🔍" },
  { href: "/lists",   label: "Listeler", icon: "📋" },
  { href: "/alerts",  label: "Alarmlar", icon: "🔔" },
  { href: "/profile", label: "Profil",   icon: "👤" },
];
export default function BottomNav() {
  const p = usePathname();
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-40">
      <div className="max-w-md mx-auto grid grid-cols-4">
        {TABS.map(t => {
          const active = t.href === "/" ? p === "/" : p.startsWith(t.href);
          return (
            <Link key={t.href} href={t.href}
              className={"flex flex-col items-center py-2 " +
                (active ? "text-emerald-600" : "text-gray-500")}>
              <span className="text-xl">{t.icon}</span>
              <span className="text-[11px] mt-0.5">{t.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
