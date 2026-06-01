/** Authenticated product shell lives under this path (see middleware). */
export const APP_BASE = "/app";

/** Main Koraku chat (not Connections / Automations / …). */
export function isAppChatRoute(pathname: string): boolean {
  return pathname === APP_BASE || pathname === `${APP_BASE}/`;
}

