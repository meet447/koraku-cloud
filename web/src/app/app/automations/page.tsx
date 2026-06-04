import type { Metadata } from "next";
import { appPageMetadata } from "@/lib/app-page-metadata";
import { AutomationsPageClient } from "./AutomationsPageClient";

export const metadata: Metadata = appPageMetadata(
  "Automations",
  "Create and manage Koraku automations.",
);

export default function AutomationsPage() {
  return <AutomationsPageClient />;
}
