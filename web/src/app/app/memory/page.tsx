import type { Metadata } from "next";
import { appPageMetadata } from "@/lib/app-page-metadata";
import { MemoryPageClient } from "./MemoryPageClient";

export const metadata: Metadata = appPageMetadata(
  "Memory",
  "Browse and search facts Koraku remembers across your conversations.",
);

export default function MemoryPage() {
  return <MemoryPageClient />;
}
