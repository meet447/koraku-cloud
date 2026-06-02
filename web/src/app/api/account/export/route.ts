import { KORAKU_COPY } from "@/lib/korakuBrand";
import { requireSupabaseAuth } from "@/lib/supabase/server";

export const runtime = "nodejs";

export async function GET() {
  const auth = await requireSupabaseAuth();
  if (!auth.ok) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  const { supabase, userId } = auth;

  const { data: userThreads, error: threadsErr } = await supabase
    .from("chat_thread")
    .select("id")
    .eq("user_id", userId);

  if (threadsErr) {
    return Response.json({ error: "Export failed", details: [threadsErr.message] }, { status: 500 });
  }

  const threadIds = (userThreads ?? []).map((t) => t.id);

  const [threads, messages, personalization, automations, automationRuns] = await Promise.all([
    supabase
      .from("chat_thread")
      .select("*")
      .eq("user_id", userId)
      .order("updated_at", { ascending: false }),
    threadIds.length > 0
      ? supabase
          .from("chat_message")
          .select("*")
          .in("thread_id", threadIds)
          .order("created_at", { ascending: true })
      : Promise.resolve({ data: [], error: null }),
    supabase
      .from("koraku_personalization")
      .select("*")
      .eq("user_id", userId)
      .order("updated_at", { ascending: false }),
    supabase
      .from("koraku_automation")
      .select("*")
      .eq("user_id", userId)
      .order("updated_at", { ascending: false }),
    supabase
      .from("koraku_automation_run")
      .select("*")
      .eq("user_id", userId)
      .order("started_at", { ascending: false })
      .limit(1000),
  ]);

  const errors = [threads.error, messages.error, personalization.error, automations.error, automationRuns.error]
    .filter(Boolean)
    .map((e) => e?.message);

  if (errors.length > 0) {
    return Response.json({ error: "Export failed", details: errors }, { status: 500 });
  }

  return Response.json({
    exported_at: new Date().toISOString(),
    user_id: userId,
    retention_note: KORAKU_COPY.exportNote,
    chat_threads: threads.data ?? [],
    chat_messages: messages.data ?? [],
    personalization: personalization.data ?? [],
    automations: automations.data ?? [],
    automation_runs: automationRuns.data ?? [],
  });
}
