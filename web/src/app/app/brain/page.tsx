import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { APP_BASE } from "@/lib/app-path";
import { appPageMetadata } from "@/lib/app-page-metadata";

export const metadata: Metadata = appPageMetadata(
  "Brain",
  "Redirect to your Koraku memory workspace.",
);

/** Legacy route — memory UI moved to /app/memory */
export default function BrainRedirectPage() {
  redirect(`${APP_BASE}/memory`);
}
