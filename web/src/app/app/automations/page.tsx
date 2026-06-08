import type { Metadata } from "next";
import dynamic from "next/dynamic";
import { AutomationsPageSkeleton } from "@/components/AutomationsSkeleton";
import { appPageMetadata } from "@/lib/app-page-metadata";

const AutomationsPageClient = dynamic(
  () =>
    import("./AutomationsPageClient").then((mod) => mod.AutomationsPageClient),
  {
    loading: () => (
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex shrink-0 items-center justify-between border-b border-neutral-200/50 bg-white px-6 py-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-orange-700">Automations</p>
            <h1 className="mt-1 text-xl font-bold tracking-tight text-koraku-ink">Scheduled workflows</h1>
          </div>
        </header>
        <AutomationsPageSkeleton />
      </div>
    ),
  },
);

export const metadata: Metadata = appPageMetadata(
  "Automations",
  "Create and manage Koraku automations.",
);

export default function AutomationsPage() {
  return <AutomationsPageClient />;
}
