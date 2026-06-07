type CacheEntry<T> = { value: T; at: number };

const store = new Map<string, CacheEntry<unknown>>();

export function getClientCache<T>(key: string, maxAgeMs: number): T | null {
  const entry = store.get(key);
  if (!entry) return null;
  if (Date.now() - entry.at > maxAgeMs) {
    store.delete(key);
    return null;
  }
  return entry.value as T;
}

export function setClientCache<T>(key: string, value: T): void {
  store.set(key, { value, at: Date.now() });
}

export function invalidateClientCache(key: string): void {
  store.delete(key);
}
