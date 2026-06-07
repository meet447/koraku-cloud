import { Redis, type RedisOptions } from "ioredis";

let _redis: Redis | null = null;
let _redisDisabled = false;

function redisOptions(url: string): RedisOptions {
  return {
    maxRetriesPerRequest: 1,
    enableOfflineQueue: false,
    connectTimeout: 5_000,
    ...(url.startsWith("rediss://") ? { tls: {} } : {}),
  };
}

function client(): Redis | null {
  if (_redisDisabled) {
    return null;
  }
  if (_redis) {
    return _redis;
  }
  const url = process.env.REDIS_URL?.trim();
  if (!url) {
    return null;
  }
  try {
    const r = new Redis(url, redisOptions(url));
    r.on("error", () => {
      _redisDisabled = true;
      try {
        r.disconnect();
      } catch {
        /* ignore */
      }
      _redis = null;
    });
    _redis = r;
    return _redis;
  } catch {
    _redisDisabled = true;
    return null;
  }
}

export async function getCachedJson<T>(key: string): Promise<T | null> {
  try {
    const r = client();
    if (!r) return null;
    const raw = await r.get(key);
    if (raw == null) return null;
    try {
      return JSON.parse(raw) as T;
    } catch {
      return null;
    }
  } catch {
    return null;
  }
}

export async function setCachedJson(
  key: string,
  value: unknown,
  ttlSec: number,
): Promise<void> {
  try {
    const r = client();
    if (!r) return;
    await r.set(key, JSON.stringify(value), "EX", ttlSec);
  } catch {
    /* cache is optional */
  }
}

export async function deleteCachedKeys(...keys: string[]): Promise<void> {
  try {
    const r = client();
    if (!r || keys.length === 0) return;
    await r.del(...keys);
  } catch {
    /* cache is optional */
  }
}

/** Drop sidebar thread-list cache for one org scope (matches GET ``threads:${orgId}:${userId}``). */
export async function invalidateUserThreadList(
  userId: string,
  orgId?: string | null,
): Promise<void> {
  const uid = userId.trim();
  const keys = new Set<string>([`threads:${uid}`]);
  const oid = (orgId ?? "").trim();
  if (oid) {
    keys.add(`threads:${oid}:${uid}`);
  }
  await deleteCachedKeys(...keys);
}

export function threadMessagesCacheKey(
  orgId: string,
  userId: string,
  threadId: string,
): string {
  return `thread-messages:${orgId}:${userId}:${threadId}`;
}

export async function invalidateThreadMessages(
  userId: string,
  orgId: string,
  threadId: string,
): Promise<void> {
  await deleteCachedKeys(threadMessagesCacheKey(orgId, userId, threadId));
}

export function userBffCacheKey(scope: string, userId: string): string {
  return `bff:${scope}:${userId}`;
}

export async function invalidateUserBffCache(scope: string, userId: string): Promise<void> {
  await deleteCachedKeys(userBffCacheKey(scope, userId));
}

/** Clear all org-scoped thread list keys for a user (account delete, etc.). */
export async function invalidateAllUserThreadLists(userId: string): Promise<void> {
  try {
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
  } catch {
    /* cache is optional */
  }
}
