"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

// Tarayıcının yerleşik barkod okuyucusu (Android Chrome); yoksa ZXing kütüphanesi kullanılır
type Detector = { detect: (src: HTMLVideoElement) => Promise<{ rawValue: string }[]> };
declare global {
  interface Window { BarcodeDetector?: new (opts: { formats: string[] }) => Detector; }
}
const FORMATS = ["ean_13", "ean_8", "upc_a", "upc_e"];

/** "Barkod Okut": kamerayla okutur ya da numara elle yazılır, bulunan ürünün sayfası açılır. */
export default function BarcodeScanner({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const video = useRef<HTMLVideoElement>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [manual, setManual] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const busy = useRef(false);

  const lookup = async (raw: string) => {
    const code = raw.replace(/\D/g, "");
    if (busy.current || code.length < 8) return;
    busy.current = true;
    setStatus("Aranıyor: " + code);
    try {
      const found = await api.findBarcode(code);
      onClose();
      router.push("/products/" + found.group_id);
    } catch (e) {
      setStatus((e as Error).message);
      setTimeout(() => { busy.current = false; }, 1500); // aynı barkodu hemen yeniden aramasın
    }
  };

  useEffect(() => {
    let stopped = false;
    let stream: MediaStream | null = null;
    let zxingControls: { stop: () => void } | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;

    (async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        setCameraError("Bu tarayıcı kameraya erişemiyor. Barkod numarasını aşağıya yazabilirsiniz.");
        return;
      }
      try {
        if (window.BarcodeDetector) {
          stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
          if (stopped || !video.current) return;
          video.current.srcObject = stream;
          await video.current.play();
          const detector = new window.BarcodeDetector({ formats: FORMATS });
          const tick = async () => {
            if (stopped || !video.current) return;
            try {
              const codes = await detector.detect(video.current);
              if (codes[0]) await lookup(codes[0].rawValue);
            } catch {}
            timer = setTimeout(tick, 300);
          };
          tick();
        } else {
          const { BrowserMultiFormatReader } = await import("@zxing/browser");
          if (stopped || !video.current) return;
          const reader = new BrowserMultiFormatReader();
          zxingControls = await reader.decodeFromConstraints(
            { video: { facingMode: "environment" } }, video.current,
            result => { if (result) lookup(result.getText()); },
          );
          if (stopped) zxingControls.stop();
        }
      } catch {
        setCameraError(
          "Kamera açılamadı. Kamera izni verin; telefonda adres https:// ile başlamalı. " +
          "Barkod numarasını aşağıya da yazabilirsiniz.",
        );
      }
    })();

    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
      zxingControls?.stop();
      stream?.getTracks().forEach(t => t.stop());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="fixed inset-0 bg-black/70 flex items-end z-50" onClick={onClose}>
      <div className="bg-white w-full max-w-md mx-auto rounded-t-2xl p-4" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-3">
          <div>
            <div className="text-lg font-bold">Barkod Okut</div>
            <div className="text-xs text-gray-500">Ürünün barkodunu kameraya gösterin</div>
          </div>
          <button onClick={onClose} aria-label="Kapat" className="text-gray-400 text-2xl">&times;</button>
        </div>
        {cameraError ? (
          <div className="text-sm text-orange-700 bg-orange-50 border border-orange-200 rounded-lg p-3 mb-3">{cameraError}</div>
        ) : (
          <div className="relative rounded-xl overflow-hidden bg-black mb-3 aspect-[4/3]">
            <video ref={video} muted playsInline className="w-full h-full object-cover" />
            <div className="absolute inset-x-8 top-1/2 -translate-y-1/2 h-24 border-2 border-emerald-400 rounded-lg" />
          </div>
        )}
        <form onSubmit={e => { e.preventDefault(); busy.current = false; lookup(manual); }} className="flex gap-2">
          <input value={manual} onChange={e => setManual(e.target.value)} inputMode="numeric"
            placeholder="Barkod numarası (örn. 8690504...)"
            className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm" />
          <button className="bg-emerald-600 text-white px-4 rounded-lg text-sm font-semibold">Ara</button>
        </form>
        {status && <div className="text-sm text-gray-600 mt-2 text-center">{status}</div>}
      </div>
    </div>
  );
}
