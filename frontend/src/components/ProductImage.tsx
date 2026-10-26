"use client";
import { useState } from "react";

// Ürün fotoğrafı (marketfiyati); yoksa ya da açılmazsa kategori simgesi
export default function ProductImage({ src, icon, size = 48 }: { src: string | null | undefined; icon: string; size?: number }) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) {
    return (
      <div className="flex items-center justify-center shrink-0" style={{ width: size, height: size, fontSize: size * 0.7 }}>
        {icon}
      </div>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt="" loading="lazy" onError={() => setFailed(true)}
      className="object-contain rounded-lg bg-white shrink-0" style={{ width: size, height: size }} />
  );
}
