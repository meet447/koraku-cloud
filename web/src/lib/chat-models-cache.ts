import { getClientCache, setClientCache } from "@/lib/client-cache";
import { korakuFetch } from "@/lib/koraku-fetch";

const CACHE_KEY = "koraku:chat-models";
const CACHE_TTL_MS = 5 * 60 * 1000;

export type ChatModelsCatalog = {
  providers?: Array<{
    id: string;
    logo_url?: string;
    label?: string;
    configured: boolean;
    models: string[];
    entries?: Array<{ id: string; logo_url?: string; label?: string }>;
  }>;
  models?: string[];
  active_provider?: string;
  default_model?: string;
};

let inflight: Promise<ChatModelsCatalog | null> | null = null;

export async function fetchChatModelsCatalog(options?: {
  force?: boolean;
}): Promise<ChatModelsCatalog | null> {
  if (!options?.force) {
    const cached = getClientCache<ChatModelsCatalog>(CACHE_KEY, CACHE_TTL_MS);
    if (cached) return cached;
  }
  if (!options?.force && inflight) return inflight;

  inflight = (async () => {
    try {
      const response = await korakuFetch("/koraku-api/api/chat-models", { method: "GET" });
      if (!response.ok) return null;
      const data = (await response.json()) as ChatModelsCatalog;
      setClientCache(CACHE_KEY, data);
      return data;
    } catch {
      return null;
    } finally {
      inflight = null;
    }
  })();

  return inflight;
}

export function prefetchChatModelsCatalog(): void {
  void fetchChatModelsCatalog();
}
