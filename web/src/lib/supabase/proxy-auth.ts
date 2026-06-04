import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { cookies } from "next/headers";
import { applyTenantHeadersFromCookies } from "@/lib/tenant/server";

/**
 * Sets ``Authorization: Bearer <access_token>`` from the Supabase cookie session when present.
 * Use in Route Handlers that proxy to the Python API so the backend can verify the user
 * even when the browser request omits ``Authorization``.
 */
export async function applySupabaseBearerFromCookies(headers: Headers): Promise<boolean> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim();
  if (!url || !key) {
    return false;
  }

  const cookieStore = await cookies();
  const supabase = createServerClient(url, key, {
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

  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();
  if (error || !user) {
    return false;
  }
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (session?.access_token) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }
  await applyTenantHeadersFromCookies(headers);
  return Boolean(session?.access_token);
}

/** JSON 401 when Supabase is configured but the caller has no valid session. */
export function proxyUnauthorizedResponse(): Response {
  return Response.json({ detail: "Sign in required." }, { status: 401 });
}
