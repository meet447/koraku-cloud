import { invalidateUserThreadList } from "@/lib/koraku-redis";
import { safeError } from "@/lib/safe-log";
import { requireSupabaseAuth } from "@/lib/supabase/server";

export const runtime = "nodejs";

export async function GET(
  _req: Request,
  ctx: { params: Promise<{ threadId: string }> },
) {
  const auth = await requireSupabaseAuth();
  if (!auth.ok) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  const { supabase } = auth;
  const { threadId } = await ctx.params;

  const { data: thread, error: threadErr } = await supabase
    .from("chat_thread")
    .select("id")
    .eq("id", threadId)
    .maybeSingle();

  if (threadErr || !thread) {
    return Response.json({ error: "Not found" }, { status: 404 });
  }

  const { data: messages, error } = await supabase
    .from("chat_message")
    .select("id, role, content_json, created_at")
    .eq("thread_id", threadId)
    .order("created_at", { ascending: true });

  if (error) {
    safeError("[chat_message GET]", error);
    return Response.json({ error: "Database error" }, { status: 500 });
  }

  return Response.json({
    messages: (messages ?? []).map((m) => ({
      id: m.id,
      role: m.role,
      contentJson: m.content_json,
      createdAt: m.created_at == null ? null : String(m.created_at),
    })),
  });
}

export async function POST(
  req: Request,
  ctx: { params: Promise<{ threadId: string }> },
) {
  const auth = await requireSupabaseAuth();
  if (!auth.ok) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  const { supabase, userId } = auth;
  const { threadId } = await ctx.params;

  const { data: thread, error: threadErr } = await supabase
    .from("chat_thread")
    .select("id")
    .eq("id", threadId)
    .maybeSingle();

  if (threadErr || !thread) {
    return Response.json({ error: "Not found" }, { status: 404 });
  }

  const body = (await req.json()) as {
    messages?: Array<{ id: string; role: string; contentJson: unknown }>;
    title?: string;
  };
  const list = body.messages;
  if (!Array.isArray(list) || list.length === 0) {
    return Response.json({ error: "messages required" }, { status: 400 });
  }

  const { error: delErr } = await supabase
    .from("chat_message")
    .delete()
    .eq("thread_id", threadId);

  if (delErr) {
    safeError("[chat_message DELETE]", delErr);
    return Response.json({ error: "Database error" }, { status: 500 });
  }

  const rows = list.map((m) => ({
    id: m.id,
    thread_id: threadId,
    role: m.role,
    content_json: m.contentJson,
  }));

  const { error: insErr } = await supabase.from("chat_message").insert(rows);

  if (insErr) {
    safeError("[chat_message INSERT]", insErr);
    return Response.json({ error: "Database error" }, { status: 500 });
  }

  const title =
    typeof body.title === "string" && body.title.trim()
      ? body.title.trim().slice(0, 200)
      : null;

  const { error: upErr } = await supabase
    .from("chat_thread")
    .update(
      title
        ? { title, updated_at: new Date().toISOString() }
        : { updated_at: new Date().toISOString() },
    )
    .eq("id", threadId);

  if (upErr) {
    safeError("[chat_thread UPDATE]", upErr);
    return Response.json({ error: "Database error" }, { status: 500 });
  }

  await invalidateUserThreadList(userId);
  return Response.json({ ok: true });
}
