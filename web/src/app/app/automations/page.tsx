import type { Metadata } from "next";
import dynamic from "next/dynamic";
import { appPageMetadata } from "@/lib/app-page-metadata";

const AutomationsPageClient = dynamic(
  () =>
    import("./AutomationsPageClient").then((mod) => mod.AutomationsPageClient),
  {
    loading: () => (
      <div className="flex min-h-0 flex-1 items-center justify-center bg-white text-sm font-medium text-neutral-500">
        Loading automations…
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
