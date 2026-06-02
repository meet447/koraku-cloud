import type { SupabaseClient } from "@supabase/supabase-js";
import { resolveActiveOrgId } from "@/lib/tenant/server";
import { requireSupabaseAuth } from "@/lib/supabase/server";

export type AuthedOrgContext = {
  supabase: SupabaseClient;
  userId: string;
  orgId: string;
};

type AuthedOrgResult =
  | { ok: true; ctx: AuthedOrgContext }
  | { ok: false; response: Response };

/** Require signed-in user and resolvable organization for BFF `/api/*` routes. */
export async function requireAuthedOrg(): Promise<AuthedOrgResult> {
  const auth = await requireSupabaseAuth();
  if (!auth.ok) {
    return {
      ok: false,
      response: Response.json({ error: "Unauthorized" }, { status: 401 }),
    };
  }

  const orgId = await resolveActiveOrgId(auth.supabase, auth.userId);
  if (!orgId) {
    return {
      ok: false,
      response: Response.json({ error: "Organization unavailable" }, { status: 503 }),
    };
  }

  return {
    ok: true,
    ctx: { supabase: auth.supabase, userId: auth.userId, orgId },
  };
}
