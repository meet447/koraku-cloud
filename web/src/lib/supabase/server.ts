import { createServerClient, type CookieOptions } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";

export async function createServerSupabase() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim();
  if (!url || !key) {
    throw new Error(
      "Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY (e.g. in web/.env.local).",
    );
  }

  const cookieStore = await cookies();

  return createServerClient(url, key, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
        try {
          cookiesToSet.forEach(({ name, value, options }) => {
            cookieStore.set(name, value, options);
          });
        } catch {
          /* Server Components may call read-only cookie APIs */
        }
      },
    },
  });
}

/** Resolves the signed-in user from the JWT (server-side). */
export async function getAuthenticatedUserId(): Promise<string | null> {
  const auth = await requireSupabaseAuth();
  return auth.ok ? auth.userId : null;
}

/**
 * Supabase client bound to the request cookies plus `auth.uid()` for RLS.
 * Use this (not a service-role client) for `public` chat tables.
 */
export async function requireSupabaseAuth(): Promise<
  | { ok: true; supabase: SupabaseClient; userId: string }
  | { ok: false }
> {
  const supabase = await createServerSupabase();
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();
  if (error || !user?.id) return { ok: false };
  return { ok: true, supabase, userId: user.id };
}
