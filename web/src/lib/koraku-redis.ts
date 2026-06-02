import { Redis } from "ioredis";

let _redis: Redis | null = null;

function client(): Redis | null {
  if (_redis) {
    return _redis;
  }
  const url = process.env.REDIS_URL?.trim();
  if (!url) {
    return null;
  }
  _redis = new Redis(url, { maxRetriesPerRequest: 20 });
  return _redis;
}

export function isRedisConfigured(): boolean {
  return Boolean(process.env.REDIS_URL?.trim());
}

export async function getCachedJson<T>(key: string): Promise<T | null> {
  const r = client();
  if (!r) return null;
  const raw = await r.get(key);
  if (raw == null) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export async function setCachedJson(
  key: string,
  value: unknown,
  ttlSec: number,
): Promise<void> {
  const r = client();
  if (!r) return;
  await r.set(key, JSON.stringify(value), "EX", ttlSec);
}

/** Drop sidebar thread-list cache for one org scope (matches GET ``threads:${orgId}:${userId}``). */
export async function invalidateUserThreadList(
  userId: string,
  orgId?: string | null,
): Promise<void> {
  const r = client();
  if (!r) return;
  const uid = userId.trim();
  const keys = new Set<string>([`threads:${uid}`]);
  const oid = (orgId ?? "").trim();
  if (oid) {
    keys.add(`threads:${oid}:${uid}`);
  }
  if (keys.size > 0) {
    await r.del(...keys);
  }
}

/** Clear all org-scoped thread list keys for a user (account delete, etc.). */
export async function invalidateAllUserThreadLists(userId: string): Promise<void> {
  const r = client();
  if (!r) return;
  const uid = userId.trim();
  const toDelete = new Set<string>([`threads:${uid}`]);
  let cursor = "0";
  const pattern = `threads:*:${uid}`;
  do {
    const [next, found] = await r.scan(cursor, "MATCH", pattern, "COUNT", 100);
    cursor = next;
    for (const k of found) {
      toDelete.add(k);
    }
  } while (cursor !== "0");
  if (toDelete.size > 0) {
    await r.del(...toDelete);
  }
}
