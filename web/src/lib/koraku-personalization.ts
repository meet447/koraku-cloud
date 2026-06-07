import { korakuFetchJson, korakuFetchOk } from "@/lib/koraku-fetch";
import { getClientCache, invalidateClientCache, setClientCache } from "@/lib/client-cache";

export type PersonalizationPayload = {
  agent_name: string;
  memory: string;
  soul: string;
};

const CACHE_KEY = "koraku:personalization";
const CACHE_TTL_MS = 60_000;

export async function loadPersonalization(options?: {
  force?: boolean;
}): Promise<PersonalizationPayload> {
  if (!options?.force) {
    const cached = getClientCache<PersonalizationPayload>(CACHE_KEY, CACHE_TTL_MS);
    if (cached) return cached;
  }
  const data = await korakuFetchJson<PersonalizationPayload>("/koraku-api/api/personalization");
  const payload = {
    agent_name: data.agent_name ?? "",
    memory: data.memory ?? "",
    soul: data.soul ?? "",
  };
  setClientCache(CACHE_KEY, payload);
  return payload;
}

export async function savePersonalization(payload: PersonalizationPayload): Promise<void> {
  await korakuFetchOk("/koraku-api/api/personalization", {
    method: "PUT",
    json: payload,
  });
  setClientCache(CACHE_KEY, payload);
}

export function invalidatePersonalizationCache(): void {
  invalidateClientCache(CACHE_KEY);
}
