import { isDetachedRunsRedisCapable } from "@/lib/koraku-health";

export type DetachedChatMode = "default" | "off" | "always" | "heavy";

let detachedRunsRedisCapable: boolean | null = null;

export async function refreshDetachedRunsCapability(): Promise<void> {
  detachedRunsRedisCapable = await isDetachedRunsRedisCapable();
}

export function detachedChatMode(): DetachedChatMode {
  const v = (process.env.NEXT_PUBLIC_KORAKU_DETACHED_CHAT ?? "").trim().toLowerCase();
  if (v === "off" || v === "0" || v === "false") return "off";
  if (v === "1" || v === "true" || v === "yes" || v === "always") return "always";
  if (v === "heavy" || v === "long" || v === "auto") return "heavy";
  return "default";
}

export function shouldUseDetachedStreamingForPayload(
  textLen: number,
  imageCount: number,
  persistenceEnabled: boolean,
): boolean {
  const mode = detachedChatMode();
  if (mode === "always") return true;
  if (mode === "heavy") {
    return textLen >= 3200 || imageCount > 0;
  }
  if (mode === "off") return false;
  if (!persistenceEnabled) return false;
  if (detachedRunsRedisCapable === false) return false;
  return true;
}

export async function fetchDetachedRunStatusJson(
  runId: string,
  authHeaders: Record<string, string>,
): Promise<{ state?: string; hint?: string } | null> {
  try {
    const r = await fetch(`/koraku-api/runs/${encodeURIComponent(runId)}/status`, {
      method: "GET",
      headers: { Accept: "application/json", ...authHeaders },
    });
    if (!r.ok) return null;
    return (await r.json()) as { state?: string; hint?: string };
  } catch {
    return null;
  }
}
