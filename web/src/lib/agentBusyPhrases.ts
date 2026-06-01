/** Short status lines inspired by coding-agent UIs (rotate while a run is in flight). */
export const AGENT_BUSY_PHRASES = [
  "Working",
  "Crunching",
  "Thinking",
  "Reasoning",
  "Running tools",
  "Reading context",
  "Stitching an answer",
  "Checking details",
  "Almost there",
  "Composing",
  "Digging in",
  "On it",
] as const;

export function formatElapsedClock(ms: number): string {
  const clamped = Math.max(0, ms);
  const totalS = Math.floor(clamped / 1000);
  const m = Math.floor(totalS / 60);
  const s = totalS % 60;
  if (m > 0) return `${m}:${String(s).padStart(2, "0")}`;
  return `0:${String(s).padStart(2, "0")}`;
}
