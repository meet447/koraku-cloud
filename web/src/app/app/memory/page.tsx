"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { APP_BASE } from "@/lib/app-path";
import { KORAKU_COPY } from "@/lib/korakuBrand";
import { KorakuPageHeader } from "@/components/KorakuPageHeader";

const MemoryGraphPanel = dynamic(() => import("@/components/MemoryGraphPanel"), {
  ssr: false,
  loading: () => (
    <section className="flex h-[min(60vh,560px)] min-h-[360px] items-center justify-center rounded-[28px] bg-koraku-panel ring-1 ring-neutral-200/80">
      <p className="text-sm font-semibold text-koraku-muted">Loading memory graph…</p>
    </section>
  ),
});

export default function MemoryPage() {
  const [query, setQuery] = useState("");

  return (
    <main className="min-h-0 flex-1 overflow-y-auto bg-[#fbfaf6] px-6 py-10">
      <div className="mx-auto max-w-5xl">
        <KorakuPageHeader
          eyebrow="Memory"
          title="Your learned second brain"
          description={KORAKU_COPY.memoryIntro}
          action={
            <Link
              href={`${APP_BASE}/personalization`}
              className="inline-flex items-center justify-center rounded-full border border-neutral-200/90 bg-white px-5 py-2.5 text-sm font-semibold text-koraku-ink shadow-sm transition hover:border-neutral-300 hover:bg-neutral-50"
            >
              Personalization
            </Link>
          }
        />

        <div className="relative mt-8">
          <Search
            className="pointer-events-none absolute left-4 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-neutral-400"
            strokeWidth={2}
            aria-hidden
          />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search memories…"
            className="w-full rounded-full border border-neutral-200/90 bg-white py-3.5 pl-11 pr-5 text-[15px] font-medium text-koraku-ink shadow-sm outline-none transition placeholder:text-neutral-400 focus:border-neutral-300 focus:ring-2 focus:ring-orange-200/60"
          />
        </div>

        <div className="mt-6">
          <MemoryGraphPanel searchQuery={query} />
        </div>
      </div>
    </main>
  );
}
