import { cookies } from "next/headers";
import { ORG_ID_COOKIE } from "@/lib/tenant/constants";
import { ensureDefaultOrgId } from "@/lib/tenant/server";
import { requireSupabaseAuth } from "@/lib/supabase/server";

/** Ensure org cookie exists for signed-in app sessions (server layout). */
export async function bootstrapOrgCookie(): Promise<void> {
  const auth = await requireSupabaseAuth();
  if (!auth.ok) return;

  const jar = await cookies();
  if (jar.get(ORG_ID_COOKIE)?.value?.trim()) return;

  const orgId = await ensureDefaultOrgId(auth.supabase, auth.userId);
  if (!orgId) return;

  jar.set(ORG_ID_COOKIE, orgId, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 365,
  });
}
