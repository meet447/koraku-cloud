import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { cookies } from "next/headers";
import { applyTenantHeadersFromCookies } from "@/lib/tenant/server";

/**
 * Sets ``Authorization: Bearer <access_token>`` from the Supabase cookie session when present.
 * Use in Route Handlers that proxy to the Python API so the backend can verify the user
 * even when the browser request omits ``Authorization``.
 */
export async function applySupabaseBearerFromCookies(headers: Headers): Promise<void> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim();
  if (!url || !key) {
    return;
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
    data: { session },
  } = await supabase.auth.getSession();
  if (session?.access_token) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }
  await applyTenantHeadersFromCookies(headers);
}
