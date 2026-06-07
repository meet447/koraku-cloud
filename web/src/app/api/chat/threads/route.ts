import {
  getCachedJson,
  invalidateUserThreadList,
  setCachedJson,
} from "@/lib/koraku-redis";
import { fetchChatThreadsForOrg } from "@/lib/chat-threads-query";
import { safeError } from "@/lib/safe-log";
import { requireAuthedOrg } from "@/lib/supabase/route-auth";

export const runtime = "nodejs";

export async function GET() {
  const authed = await requireAuthedOrg();
  if (!authed.ok) {
    return authed.response;
  }
  const { supabase, userId, orgId } = authed.ctx;

  const cacheKey = `threads:${orgId}:${userId}`;
  const cached = await getCachedJson<
    {
      id: string;
      title: string;
      updatedAt: string | null;
      channel?: string;
      pinned?: boolean;
    }[]
  >(cacheKey);
  if (cached) {
    return Response.json({ threads: cached });
  }

  const { threads, error } = await fetchChatThreadsForOrg(supabase, orgId);

  if (error) {
    safeError("[chat_thread GET]", error);
    return Response.json({ error: "Database error" }, { status: 500 });
  }
  await setCachedJson(cacheKey, threads, 30);
  return Response.json({ threads });
}

export async function POST(req: Request) {
  const authed = await requireAuthedOrg();
  if (!authed.ok) {
    return authed.response;
  }
  const { supabase, userId, orgId } = authed.ctx;

  let title = "New chat";
  let id = crypto.randomUUID();
  try {
    const body = (await req.json()) as { title?: string; id?: string };
    if (typeof body.id === "string") {
      const candidate = body.id.trim();
      if (
        /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
          candidate,
        )
      ) {
        id = candidate;
      }
    }
    if (typeof body.title === "string" && body.title.trim()) {
      title = body.title.trim().slice(0, 200);
    }
  } catch {
    /* ignore empty body */
  }

  const { data, error } = await supabase
    .from("chat_thread")
    .upsert(
      { id, user_id: userId, org_id: orgId, title },
      { onConflict: "id" },
    )
    .select("id, title")
    .single();

  if (error || !data) {
    safeError("[chat_thread POST]", error);
    return Response.json({ error: "Database error" }, { status: 500 });
  }

  await invalidateUserThreadList(userId, orgId);
  return Response.json({ id: data.id, title: data.title });
}
