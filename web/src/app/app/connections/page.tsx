import type { Metadata } from "next";
import dynamic from "next/dynamic";
import { appPageMetadata } from "@/lib/app-page-metadata";

const ConnectionsPageClient = dynamic(
  () =>
    import("./ConnectionsPageClient").then((mod) => mod.ConnectionsPageClient),
  {
    loading: () => (
      <div className="flex min-h-[40vh] items-center justify-center text-sm font-medium text-neutral-500">
        Loading integrations…
      </div>
    ),
  },
);

export const metadata: Metadata = appPageMetadata(
  "Connections",
  "Connect Gmail, Slack, and other tools to Koraku.",
);

export default function ConnectionsPage() {
  return <ConnectionsPageClient />;
}
