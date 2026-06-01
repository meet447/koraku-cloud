import { requireSupabaseAuth } from "@/lib/supabase/server";

export const runtime = "nodejs";

export async function GET() {
  const auth = await requireSupabaseAuth();
  if (!auth.ok) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  const { supabase, userId } = auth;

  const [
    threads,
    messages,
    personalization,
    automations,
    automationRuns,
  ] = await Promise.all([
    supabase.from("chat_thread").select("*").order("updated_at", { ascending: false }),
    supabase.from("chat_message").select("*").order("created_at", { ascending: true }),
    supabase.from("koraku_personalization").select("*").eq("user_id", userId).maybeSingle(),
    supabase.from("koraku_automation").select("*").order("updated_at", { ascending: false }),
    supabase.from("koraku_automation_run").select("*").order("started_at", { ascending: false }).limit(1000),
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
    retention_note:
      "This export includes Supabase-backed Koraku data available to the signed-in user. Provider-side LLM, Composio, and sandbox retention is governed by those services.",
    chat_threads: threads.data ?? [],
    chat_messages: messages.data ?? [],
    personalization: personalization.data ?? null,
    automations: automations.data ?? [],
    automation_runs: automationRuns.data ?? [],
  });
}
