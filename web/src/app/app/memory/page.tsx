"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import Link from "next/link";
import { APP_BASE } from "@/lib/app-path";

const MemoryGraphPanel = dynamic(() => import("@/components/MemoryGraphPanel"), {
  ssr: false,
  loading: () => (
    <section className="flex h-[min(60vh,560px)] min-h-[360px] items-center justify-center rounded-3xl bg-neutral-950 ring-1 ring-neutral-800">
      <p className="text-sm font-semibold text-white/60">Loading memory graph…</p>
    </section>
  ),
});

export default function MemoryPage() {
  const [query, setQuery] = useState("");

  return (
    <main className="min-h-0 flex-1 overflow-y-auto bg-white px-6 py-10">
      <div className="mx-auto max-w-5xl">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-neutral-950">Memory</h1>
            <p className="mt-2 max-w-xl text-sm font-medium leading-relaxed text-neutral-600">
              What Koraku remembers across chats (Supermemory). Name, tone, and explicit
              preferences are edited in Personalization.
            </p>
          </div>
          <Link
            href={`${APP_BASE}/personalization`}
            className="shrink-0 rounded-full border border-neutral-200 px-4 py-2 text-sm font-bold text-neutral-800 transition hover:bg-neutral-50"
          >
            Personalization
          </Link>
        </div>

        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search memories…"
          className="mt-6 w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm font-semibold outline-none focus:bg-white focus:ring-2 focus:ring-orange-200"
        />

        <div className="mt-5">
          <MemoryGraphPanel searchQuery={query} />
        </div>
      </div>
    </main>
  );
}
