import { invalidateUserThreadList } from "@/lib/koraku-redis";
import { safeError } from "@/lib/safe-log";
import { requireAuthedOrg } from "@/lib/supabase/route-auth";

export const runtime = "nodejs";

export async function DELETE(
  _req: Request,
  ctx: { params: Promise<{ threadId: string }> },
) {
  const auth = await requireAuthedOrg();
  if (!auth.ok) {
    return auth.response;
  }
  const { supabase, userId, orgId } = auth.ctx;
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

  await invalidateUserThreadList(userId, orgId);
  return Response.json({ ok: true });
}
