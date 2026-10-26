"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useLists } from "@/lib/store";

// Paylaşılan bağlantı: /lists/join?code=K7PX2M9Q -> listeye katılır ve listeyi açar
function Join() {
  const router = useRouter();
  const code = useSearchParams().get("code") || "";
  const { user, refreshLists } = useLists();
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (!user || started.current) return;
    started.current = true;
    api.joinList(code)
      .then(async l => { await refreshLists(); router.replace("/lists/" + l.id); })
      .catch(e => setError((e as Error).message));
  }, [user, code, refreshLists, router]);

  return (
    <main className="p-6 text-center">
      {error ? (
        <>
          <div className="text-3xl mb-2">😕</div>
          <div className="text-sm text-gray-700">{error}</div>
          <button onClick={() => router.push("/lists")} className="mt-4 text-emerald-600 underline text-sm">Listelere dön</button>
        </>
      ) : (
        <div className="text-gray-500">Listeye katılınıyor…</div>
      )}
    </main>
  );
}

export default function JoinPage() {
  return <Suspense fallback={<div className="p-6">Yükleniyor…</div>}><Join /></Suspense>;
}
