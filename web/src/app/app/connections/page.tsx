import type { Metadata } from "next";
import { appPageMetadata } from "@/lib/app-page-metadata";
import { ConnectionsPageClient } from "./ConnectionsPageClient";

export const metadata: Metadata = appPageMetadata(
  "Connections",
  "Connect Gmail, Slack, and other tools to Koraku.",
);

export default function ConnectionsPage() {
  return <ConnectionsPageClient />;
}
