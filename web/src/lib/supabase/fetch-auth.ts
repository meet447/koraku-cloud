import { createBrowserSupabaseClient } from "@/lib/supabase/browser";

let cachedToken: string | null = null;
let cacheAt = 0;
const CACHE_TTL_MS = 30_000;
let authListenerInstalled = false;

function readCachedAuthorization(): string | null {
  if (!cachedToken) return null;
  if (Date.now() - cacheAt > CACHE_TTL_MS) {
    cachedToken = null;
    return null;
  }
  return cachedToken;
}

function rememberAuthorization(token: string | null | undefined): void {
  cachedToken = token?.trim() || null;
  cacheAt = Date.now();
}

function ensureAuthListener(): void {
  if (authListenerInstalled || typeof window === "undefined") return;
  authListenerInstalled = true;
  try {
    const supabase = createBrowserSupabaseClient();
    supabase.auth.onAuthStateChange((_event, session) => {
      rememberAuthorization(session?.access_token);
    });
  } catch {
    /* Supabase env missing */
  }
}

/** Headers for same-origin fetch to Next or Koraku API routes that forward ``Authorization`` to Python. */
export async function supabaseAuthHeaders(): Promise<Record<string, string>> {
  ensureAuthListener();
  const cached = readCachedAuthorization();
  if (cached) {
    return { Authorization: `Bearer ${cached}` };
  }

  const h: Record<string, string> = {};
  try {
    const supabase = createBrowserSupabaseClient();
    const { data } = await supabase.auth.getSession();
    rememberAuthorization(data.session?.access_token);
    if (cachedToken) {
      h.Authorization = `Bearer ${cachedToken}`;
    }
  } catch {
    /* Supabase env missing */
  }
  return h;
}

export function invalidateSupabaseAuthCache(): void {
  cachedToken = null;
  cacheAt = 0;
}
