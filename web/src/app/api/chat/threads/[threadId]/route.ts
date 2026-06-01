import { invalidateUserThreadList } from "@/lib/koraku-redis";
import { safeError } from "@/lib/safe-log";
import { requireSupabaseAuth } from "@/lib/supabase/server";

export const runtime = "nodejs";

export async function DELETE(
  _req: Request,
  ctx: { params: Promise<{ threadId: string }> },
) {
  const auth = await requireSupabaseAuth();
  if (!auth.ok) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  const { supabase, userId } = auth;
  const { threadId } = await ctx.params;

  const { data: thread, error: selErr } = await supabase
    .from("chat_thread")
    .select("id")
    .eq("id", threadId)
    .maybeSingle();

  if (selErr || !thread) {
    return Response.json({ error: "Not found" }, { status: 404 });
  }

  const { error: delErr } = await supabase.from("chat_thread").delete().eq("id", threadId);

  if (delErr) {
    safeError("[chat_thread DELETE]", delErr);
    return Response.json({ error: "Database error" }, { status: 500 });
  }

  await invalidateUserThreadList(userId);
  return Response.json({ ok: true });
}
