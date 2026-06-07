const LAST_ACTIVE_THREAD_KEY = "koraku_last_active_thread";

export function readLastActiveThreadId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const id = window.sessionStorage.getItem(LAST_ACTIVE_THREAD_KEY)?.trim();
    return id || null;
  } catch {
    return null;
  }
}

export function rememberLastActiveThreadId(id: string): void {
  if (typeof window === "undefined") return;
  const trimmed = id.trim();
  if (!trimmed) return;
  try {
    window.sessionStorage.setItem(LAST_ACTIVE_THREAD_KEY, trimmed);
  } catch {
    /* ignore */
  }
}
