"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useLists } from "@/lib/store";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/lists";
  const { user, hydrated, login, register } = useLists();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (hydrated && user) router.replace(next.startsWith("/") ? next : "/lists");
  }, [hydrated, user, next, router]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      if (mode === "login") await login(email.trim(), password);
      else await register(email.trim(), password, fullName.trim() || undefined);
    } catch (err) {
      setError((err as Error).message);
    } finally { setBusy(false); }
  };

  return (
    <main className="p-4">
      <h1 className="text-2xl font-bold mb-1">🛒 MarketKıyas</h1>
      <p className="text-sm text-gray-500 mb-4">Listelerinizi ve tasarruf kasanızı kaydetmek için giriş yapın.</p>
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg mb-4">
        {([["login", "Giriş Yap"], ["register", "Kayıt Ol"]] as const).map(([m, label]) => (
          <button key={m} onClick={() => { setMode(m); setError(null); }}
            className={"flex-1 py-2 rounded-md text-sm font-medium " + (mode === m ? "bg-white shadow text-emerald-700" : "text-gray-600")}>
            {label}
          </button>
        ))}
      </div>
      <form onSubmit={submit} className="card p-4 space-y-3">
        {mode === "register" && (
          <input value={fullName} onChange={e => setFullName(e.target.value)} placeholder="Adınız (isteğe bağlı)"
            className="w-full border rounded-lg px-3 py-2" autoComplete="name" />
        )}
        <input value={email} onChange={e => setEmail(e.target.value)} placeholder="E-posta" type="email" required
          className="w-full border rounded-lg px-3 py-2" autoComplete="email" />
        <input value={password} onChange={e => setPassword(e.target.value)} placeholder="Şifre" type="password" required
          minLength={mode === "register" ? 8 : undefined}
          className="w-full border rounded-lg px-3 py-2" autoComplete={mode === "login" ? "current-password" : "new-password"} />
        {mode === "register" && <div className="text-xs text-gray-400">En az 8 karakter.</div>}
        {error && <div className="text-sm text-red-600">{error}</div>}
        <button disabled={busy} className="w-full bg-emerald-600 disabled:opacity-60 text-white py-3 rounded-xl font-semibold">
          {busy ? "Lütfen bekleyin…" : mode === "login" ? "Giriş Yap" : "Kayıt Ol"}
        </button>
      </form>
    </main>
  );
}

export default function LoginPage() {
  return <Suspense fallback={<div className="p-6">Yükleniyor…</div>}><LoginForm /></Suspense>;
}
