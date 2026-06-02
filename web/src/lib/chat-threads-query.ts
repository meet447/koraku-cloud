import type { SupabaseClient } from "@supabase/supabase-js";

export type ChatThreadRow = {
  id: string;
  title: string;
  updatedAt: string | null;
  channel: string;
  pinned: boolean;
};

/** True when PostgREST reports missing ``channel`` / ``pinned`` (migration not applied yet). */
function isMissingChannelColumns(error: { message?: string; code?: string } | null): boolean {
  if (!error) return false;
  const code = String(error.code || "");
  if (code === "42703" || code === "PGRST204") return true;
  const msg = String(error.message || "").toLowerCase();
  return msg.includes("channel") || msg.includes("pinned");
}

/**
 * List chat threads for an org. Uses extended columns when the SendBlue migration
 * has been applied; otherwise falls back so existing deployments keep working.
 */
export async function fetchChatThreadsForOrg(
  supabase: SupabaseClient,
  orgId: string,
): Promise<{ threads: ChatThreadRow[]; error: Error | null }> {
  const extended = await supabase
    .from("chat_thread")
    .select("id, title, updated_at, channel, pinned")
    .eq("org_id", orgId)
    .order("pinned", { ascending: false })
    .order("updated_at", { ascending: false })
    .limit(200);

  if (!extended.error) {
    const threads = (extended.data ?? []).map((r) => ({
      id: r.id,
      title: r.title,
      updatedAt: r.updated_at == null ? null : String(r.updated_at),
      channel: (r.channel as string) || "web",
      pinned: Boolean(r.pinned),
    }));
    return { threads, error: null };
  }

  if (!isMissingChannelColumns(extended.error)) {
    return { threads: [], error: extended.error };
  }

  const basic = await supabase
    .from("chat_thread")
    .select("id, title, updated_at")
    .eq("org_id", orgId)
    .order("updated_at", { ascending: false })
    .limit(200);

  if (basic.error) {
    return { threads: [], error: basic.error };
  }

  const threads = (basic.data ?? []).map((r) => ({
    id: r.id,
    title: r.title,
    updatedAt: r.updated_at == null ? null : String(r.updated_at),
    channel: "web",
    pinned: false,
  }));
  return { threads, error: null };
}
