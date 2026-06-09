import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { cookies } from "next/headers";
import { applyTenantHeadersFromCookies } from "@/lib/tenant/server";

async function createCookieSupabaseClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim();
  if (!url || !key) {
    return null;
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
          /* ignore */
        }
      },
    },
  });
}

export async function getSessionUserIdFromCookies(): Promise<string | null> {
  try {
    const supabase = await createCookieSupabaseClient();
    if (!supabase) return null;
    const {
      data: { user },
    } = await supabase.auth.getUser();
    return user?.id ?? null;
  } catch {
    return null;
  }
}

/**
 * Sets ``Authorization: Bearer <access_token>`` from the Supabase cookie session when present.
 * Use in Route Handlers that proxy to the Python API so the backend can verify the user
 * even when the browser request omits ``Authorization``.
 */
export async function applySupabaseBearerFromCookies(headers: Headers): Promise<boolean> {
  const supabase = await createCookieSupabaseClient();
  if (!supabase) {
    return false;
  }

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return false;
  }

  const {
    data: { session },
  } = await supabase.auth.getSession();
  const accessToken = session?.access_token;
  if (!accessToken) {
    return false;
  }

  headers.set("Authorization", `Bearer ${accessToken}`);
  await applyTenantHeadersFromCookies(headers, supabase, user.id);
  return true;
}

/** JSON 401 when Supabase is configured but the caller has no valid session. */
export function proxyUnauthorizedResponse(): Response {
  return Response.json({ detail: "Sign in required." }, { status: 401 });
}
