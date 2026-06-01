"use client";

import { APP_BASE } from "@/lib/app-path";

/** Safe post-login path from `?next=` (must stay under `/app`). */
export function readPostAuthRedirect(): string {
  if (typeof window === "undefined") return APP_BASE;
  const raw = new URLSearchParams(window.location.search).get("next");
  if (raw && raw.startsWith("/app")) return raw;
  return APP_BASE;
}
