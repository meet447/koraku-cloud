export type KorakuHealth = {
  llmConfigured: boolean;
  mode: string;
  llmProvider: string;
  detachedRunsRedis: boolean;
};

let cached: KorakuHealth | null = null;
let inflight: Promise<KorakuHealth | null> | null = null;

function parseHealth(data: Record<string, unknown>): KorakuHealth {
  return {
    llmConfigured: Boolean(data.llm_configured),
    mode: String(data.mode ?? "unknown"),
    llmProvider: String(data.llm_provider ?? ""),
    detachedRunsRedis: Boolean(data.detached_runs_redis),
  };
}

/** Fetch Koraku API health; dedupes concurrent requests and caches the last success. */
export async function fetchKorakuHealth(options?: {
  force?: boolean;
}): Promise<KorakuHealth | null> {
  if (!options?.force && cached) {
    return cached;
  }
  if (!options?.force && inflight) {
    return inflight;
  }

  inflight = (async () => {
    try {
      const response = await fetch("/koraku-api/health", { cache: "no-store" });
      if (!response.ok) {
        return null;
      }
      const data = (await response.json()) as Record<string, unknown>;
      cached = parseHealth(data);
      return cached;
    } catch {
      return null;
    } finally {
      inflight = null;
    }
  })();

  return inflight;
}

export async function isDetachedRunsRedisCapable(): Promise<boolean> {
  const health = await fetchKorakuHealth();
  return Boolean(health?.detachedRunsRedis);
}
