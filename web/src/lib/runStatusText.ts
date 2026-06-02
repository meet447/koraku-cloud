/** User-facing run status vs internal telemetry (tokens, mode, connection). */

const INTERNAL_PATTERNS = [
  /^Thinking… · \d+ tok$/i,
  / · up to \d+ steps$/i,
  /^Connecting…$/i,
  /^Preparing tools…$/i,
];

/** Shown in the small footer under a completed assistant message. */
export function shouldShowRunFooterStatus(statusText: string): boolean {
  const t = statusText.trim();
  if (!t) return false;
  if (t === "Done" || t === "Failed" || t === "Stopped") return true;
  if (t.includes("Reconnect") || t.includes("Subscribe")) return true;
  if (INTERNAL_PATTERNS.some((re) => re.test(t))) return false;
  if (t.endsWith("…") || t.endsWith("...")) return false;
  return false;
}

/** Label for the live busy row while the turn is in-flight. */
export function busyRowLabelFromStatus(statusText: string): string | null {
  const t = statusText.trim();
  if (!t) return null;
  if (INTERNAL_PATTERNS.some((re) => re.test(t))) return null;
  if (t === "Done" || t === "Failed" || t === "Stopped") return null;
  if (t.includes("Reconnect") || t.includes("Subscribe")) return null;
  if (t.includes(" steps")) return null;
  return t.replace(/…+$/, "").trim() || null;
}
