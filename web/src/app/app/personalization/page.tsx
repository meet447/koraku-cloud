import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { APP_BASE } from "@/lib/app-path";
import { appPageMetadata } from "@/lib/app-page-metadata";

export const metadata: Metadata = appPageMetadata(
  "Personalization",
  "Redirect to agent personalization settings.",
);

export default function PersonalizationRedirectPage() {
  redirect(`${APP_BASE}/settings/agent`);
}
