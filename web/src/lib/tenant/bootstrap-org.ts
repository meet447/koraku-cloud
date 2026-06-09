"use server";

import { resolveActiveOrgId } from "@/lib/tenant/server";
import { requireSupabaseAuth } from "@/lib/supabase/server";

/** Ensure org cookie exists and matches membership for signed-in app sessions. */
export async function bootstrapOrgCookie(): Promise<void> {
  const auth = await requireSupabaseAuth();
  if (!auth.ok) return;

  await resolveActiveOrgId(auth.supabase, auth.userId);
}
