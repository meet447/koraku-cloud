"use client";

import { APP_BASE } from "@/lib/app-path";

/** Safe post-login path from `?next=` (must stay under `/app`, no protocol tricks). */
export function readPostAuthRedirect(): string {
  if (typeof window === "undefined") return APP_BASE;
  const raw = new URLSearchParams(window.location.search).get("next")?.trim();
  if (!raw || !raw.startsWith("/app") || raw.startsWith("//") || raw.includes("://")) {
    return APP_BASE;
  }
  return raw;
}
