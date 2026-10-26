import type { Metadata, Viewport } from "next";
import "./globals.css";
import { ListProvider } from "@/lib/store";
import BottomNav from "@/components/BottomNav";

export const metadata: Metadata = {
  title: "MarketKıyas",
  description: "Market fiyat karşılaştırma",
  manifest: "/manifest.json",
};
export const viewport: Viewport = {
  width: "device-width", initialScale: 1, themeColor: "#059669",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <body>
        <ListProvider>
          <div className="max-w-md mx-auto min-h-screen pb-20">{children}</div>
          <BottomNav />
        </ListProvider>
      </body>
    </html>
  );
}
