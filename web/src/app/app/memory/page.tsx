"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import Link from "next/link";
import { APP_BASE } from "@/lib/app-path";
import { KORAKU_COPY } from "@/lib/korakuBrand";
import { KorakuAppPage } from "@/components/KorakuAppPage";
import { KorakuPageHeader } from "@/components/KorakuPageHeader";
import { KorakuSearchInput } from "@/components/KorakuSearchInput";

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
    <KorakuAppPage maxWidth="5xl">
        <KorakuPageHeader
          eyebrow="Memory"
          title="Your learned second brain"
          description={KORAKU_COPY.memoryIntro}
          action={
            <Link
              href={`${APP_BASE}/settings#personalization`}
              className="inline-flex items-center justify-center rounded-full border border-neutral-200/90 bg-white px-5 py-2.5 text-sm font-semibold text-koraku-ink shadow-sm transition hover:border-neutral-300 hover:bg-neutral-50"
            >
              Settings
            </Link>
          }
        />

        <div className="mt-8">
          <KorakuSearchInput
            value={query}
            onChange={setQuery}
            placeholder="Search memories…"
          />
        </div>

        <div className="mt-6">
          <MemoryGraphPanel searchQuery={query} />
        </div>
    </KorakuAppPage>
  );
}
