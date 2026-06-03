"use client";

import { APP_BASE, isOnboardingRoute, ONBOARDING_PATH } from "@/lib/app-path";
import { isOnboardingComplete } from "@/lib/onboarding";

/** Safe post-login path from `?next=` (must stay under `/app`, no protocol tricks). */
export function readPostAuthRedirect(): string {
  if (typeof window === "undefined") {
    return ONBOARDING_PATH;
  }
  const raw = new URLSearchParams(window.location.search).get("next")?.trim();
  const fallback = isOnboardingComplete() ? APP_BASE : ONBOARDING_PATH;
  if (!raw || !raw.startsWith("/app") || raw.startsWith("//") || raw.includes("://")) {
    return fallback;
  }
  if (!isOnboardingComplete() && !isOnboardingRoute(raw)) {
    return ONBOARDING_PATH;
  }
  return raw;
}
