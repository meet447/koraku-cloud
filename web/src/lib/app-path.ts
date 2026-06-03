/** Authenticated product shell lives under this path (see middleware). */
export const APP_BASE = "/app";

/** First-run wizard; must be completed before other `/app` routes. */
export const ONBOARDING_PATH = "/app/onboarding";

/** Any route under the authenticated app (including onboarding). */
export function isAppRoute(pathname: string): boolean {
  return pathname === APP_BASE || pathname.startsWith(`${APP_BASE}/`);
}

export function isOnboardingRoute(pathname: string): boolean {
  return pathname === ONBOARDING_PATH || pathname.startsWith(`${ONBOARDING_PATH}/`);
}

/** Main Koraku chat (not Connections / Automations / …). */
export function isAppChatRoute(pathname: string): boolean {
  return pathname === APP_BASE || pathname === `${APP_BASE}/`;
}

