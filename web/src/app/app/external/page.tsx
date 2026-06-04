import type { Metadata } from "next";
import { appPageMetadata } from "@/lib/app-page-metadata";
import { ExternalPageClient } from "./ExternalPageClient";

export const metadata: Metadata = appPageMetadata(
  "External",
  "Link your phone to message Koraku from iMessage or SMS.",
);

export default function ExternalPage() {
  return <ExternalPageClient />;
}
