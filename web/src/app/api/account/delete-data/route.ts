import { invalidateUserThreadList } from "@/lib/koraku-redis";
import { requireSupabaseAuth } from "@/lib/supabase/server";

export const runtime = "nodejs";

export async function POST() {
  const auth = await requireSupabaseAuth();
  if (!auth.ok) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  const { supabase, userId } = auth;

  const results = await Promise.all([
    supabase.from("chat_message").delete().neq("id", "__never__"),
    supabase.from("chat_thread").delete().eq("user_id", userId),
    supabase.from("koraku_personalization").delete().eq("user_id", userId),
    supabase.from("koraku_automation_run").delete().eq("user_id", userId),
    supabase.from("koraku_automation").delete().eq("user_id", userId),
  ]);

  const errors = results
    .map((r) => r.error)
    .filter(Boolean)
    .map((e) => e?.message);

  if (errors.length > 0) {
    return Response.json({ error: "Delete failed", details: errors }, { status: 500 });
  }

  await invalidateUserThreadList(userId);
  return Response.json({
    ok: true,
    note:
      "Koraku app data was deleted. Auth account removal, Composio disconnection, and provider-side retention may require separate support/admin action.",
  });
}
