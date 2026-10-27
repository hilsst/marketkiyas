"use client";
import { useEffect, useRef } from "react";

const DURATION_MS = 4000; // kutlama ekranı bu kadar kalır, sonra onDone
const CALM_DURATION_MS = 2500; // tasarruf yoksa sakin ekran

/**
 * Tarayıcılar sesi yalnızca kullanıcı dokunuşuyla başlatmaya izin verir. "Alışverişi Bitir" tıklanır
 * tıklanmaz (istekten önce) çağrılır; dönen AudioContext kutlamada kumbara sesini çalmak için kullanılır.
 */
export function prepareCelebrationAudio(): AudioContext | null {
  try {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctx) return null;
    const ctx = new Ctx();
    void ctx.resume();
    return ctx;
  } catch {
    return null;
  }
}

/** Kumbaraya düşen bozuk para: iki parlak "çın" ve ardından kısa bir şıngırtı (dosyasız, sentezle). */
function playCoinSound(ctx: AudioContext) {
  const ping = (at: number, freq: number, length: number, volume: number) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "triangle";
    osc.frequency.setValueAtTime(freq, at);
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(volume, at + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + length);
    osc.connect(gain).connect(ctx.destination);
    osc.start(at);
    osc.stop(at + length + 0.05);
  };
  const t = ctx.currentTime + 0.05;
  ping(t, 1318.5, 0.18, 0.25); // E6
  ping(t + 0.09, 1975.5, 0.5, 0.25); // B6
  [0.45, 0.55, 0.62, 0.7].forEach((d, i) => ping(t + d, 2600 + i * 180, 0.12, 0.08));
}

type Particle = { x: number; y: number; vx: number; vy: number; life: number; color: string; size: number };
const COLORS = ["#10b981", "#f59e0b", "#ef4444", "#3b82f6", "#a855f7", "#facc15", "#ec4899"];

/** Havai fişek: rastgele noktalarda patlayan, yerçekimiyle düşen renkli parçacıklar. */
function runFireworks(canvas: HTMLCanvasElement, until: number) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return () => {};
  const dpr = window.devicePixelRatio || 1;
  const resize = () => {
    canvas.width = canvas.clientWidth * dpr;
    canvas.height = canvas.clientHeight * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  };
  resize();
  const particles: Particle[] = [];
  const burst = () => {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    const cx = w * (0.15 + Math.random() * 0.7), cy = h * (0.12 + Math.random() * 0.35);
    const color = COLORS[Math.floor(Math.random() * COLORS.length)];
    for (let i = 0; i < 46; i++) {
      const a = (Math.PI * 2 * i) / 46, s = 2 + Math.random() * 3.5;
      particles.push({ x: cx, y: cy, vx: Math.cos(a) * s, vy: Math.sin(a) * s, life: 1, color, size: 2 + Math.random() * 2 });
    }
  };
  let raf = 0, nextBurst = 0;
  const tick = (now: number) => {
    if (now < until && now >= nextBurst) { burst(); nextBurst = now + 380 + Math.random() * 320; }
    ctx.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.x += p.vx; p.y += p.vy; p.vy += 0.06; p.vx *= 0.985; p.life -= 0.012;
      if (p.life <= 0) { particles.splice(i, 1); continue; }
      ctx.globalAlpha = p.life;
      ctx.fillStyle = p.color;
      ctx.beginPath(); ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2); ctx.fill();
    }
    if (now < until + 1500 || particles.length) raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
  window.addEventListener("resize", resize);
  return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", resize); };
}

/**
 * "Alışverişi Bitir" sonrası tam ekran kutlama: bu alışverişin tasarrufu, havai fişek ve kumbara sesi; birkaç
 * saniye sonra (ya da dokununca) onDone. Gösterilen tutar kasaya eklenen tasarruf, o yoksa (Farketmez kalemler,
 * haftalık sınır) bu alışverişte ortalama fiyatlara göre kazanılan. İkisi de sıfırsa sakin bir özet gösterilir.
 * "Hareketi azalt" açık cihazlarda animasyon oynatılmaz.
 */
export default function Celebration({
  savedAmount, shoppingSavings = 0, vaultTotal, note, audio, onDone,
}: {
  savedAmount: number; shoppingSavings?: number; vaultTotal: number; note?: string | null;
  audio?: AudioContext | null; onDone: () => void;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const done = useRef(onDone);
  done.current = onDone;
  const amount = savedAmount > 0 ? savedAmount : shoppingSavings;
  const festive = amount > 0;

  useEffect(() => {
    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const duration = festive ? DURATION_MS : CALM_DURATION_MS;
    let stop = () => {};
    if (festive && !reduced && canvas.current) stop = runFireworks(canvas.current, performance.now() + duration - 1200);
    if (festive && audio) {
      try { playCoinSound(audio); } catch { /* ses çalınamazsa kutlama yine sürer */ }
    }
    const timer = setTimeout(() => done.current(), duration);
    return () => { clearTimeout(timer); stop(); };
  }, [festive, audio]);

  return (
    <div role="dialog" aria-live="assertive" onClick={() => done.current()}
      className={"fixed inset-0 z-[100] flex items-center justify-center p-6 " +
        (festive ? "bg-gradient-to-b from-emerald-600 to-teal-800" : "bg-gray-900/80")}>
      {festive && <canvas ref={canvas} className="absolute inset-0 w-full h-full pointer-events-none" />}
      <div className="relative text-center text-white celebration-pop">
        {festive ? (
          <>
            <div className="text-7xl mb-3 celebration-coin">🐷</div>
            <div className="text-lg font-semibold opacity-90">
              {savedAmount > 0 ? "Tebrikler! Kumbarana eklendi" : "Tebrikler! Bu alışverişte kazancın"}
            </div>
            <div className="text-6xl font-black my-2 tracking-tight">{amount.toFixed(2)} ₺</div>
            {savedAmount <= 0 && <div className="text-xs opacity-85 -mt-1 mb-1">ortalama raf fiyatlarına göre</div>}
            <div className="text-sm opacity-90">Kumbarandaki toplam: <b>{vaultTotal.toFixed(2)} ₺</b></div>
            <div className="text-xs opacity-75 mt-1">Bu tempoyla yılda yaklaşık {(amount * 52).toFixed(0)} ₺</div>
            {note && <div className="text-[11px] opacity-70 mt-2 max-w-xs mx-auto">{note}</div>}
          </>
        ) : (
          <>
            <div className="text-6xl mb-3">✅</div>
            <div className="text-2xl font-bold">Alışveriş tamamlandı</div>
            {note && <div className="text-sm opacity-85 mt-2 max-w-xs mx-auto">{note}</div>}
          </>
        )}
        <div className="text-[11px] opacity-60 mt-6">Ana sayfaya dönülüyor…</div>
      </div>
    </div>
  );
}
