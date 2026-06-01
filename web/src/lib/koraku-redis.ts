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

export async function invalidateUserThreadList(userId: string): Promise<void> {
  const r = client();
  if (!r) return;
  await r.del(`threads:${userId}`);
}
