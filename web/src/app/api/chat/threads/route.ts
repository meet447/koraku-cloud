import {
  getCachedJson,
  invalidateUserThreadList,
  setCachedJson,
} from "@/lib/koraku-redis";
import { safeError } from "@/lib/safe-log";
import { resolveActiveOrgId } from "@/lib/tenant/server";
import { requireSupabaseAuth } from "@/lib/supabase/server";

export const runtime = "nodejs";

export async function GET() {
  const auth = await requireSupabaseAuth();
  if (!auth.ok) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  const { supabase, userId } = auth;
  const orgId = await resolveActiveOrgId(supabase, userId);
  if (!orgId) {
    return Response.json({ error: "Organization unavailable" }, { status: 503 });
  }

  const cacheKey = `threads:${orgId}:${userId}`;
  const cached = await getCachedJson<
    { id: string; title: string; updatedAt: string | null }[]
  >(cacheKey);
  if (cached) {
    return Response.json({ threads: cached });
  }

  const { data: rows, error } = await supabase
    .from("chat_thread")
    .select("id, title, updated_at")
    .eq("org_id", orgId)
    .order("updated_at", { ascending: false })
    .limit(200);

  if (error) {
    safeError("[chat_thread GET]", error);
    return Response.json({ error: "Database error" }, { status: 500 });
  }

  const threads = (rows ?? []).map((r) => ({
    id: r.id,
    title: r.title,
    updatedAt: r.updated_at == null ? null : String(r.updated_at),
  }));
  await setCachedJson(cacheKey, threads, 30);
  return Response.json({ threads });
}

export async function POST(req: Request) {
  const auth = await requireSupabaseAuth();
  if (!auth.ok) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  const { supabase, userId } = auth;
  const orgId = await resolveActiveOrgId(supabase, userId);
  if (!orgId) {
    return Response.json({ error: "Organization unavailable" }, { status: 503 });
  }

  let title = "New chat";
  try {
    const body = (await req.json()) as { title?: string };
    if (typeof body.title === "string" && body.title.trim()) {
      title = body.title.trim().slice(0, 200);
    }
  } catch {
    /* ignore empty body */
  }
  const id = crypto.randomUUID();

  const { data, error } = await supabase
    .from("chat_thread")
    .insert({ id, user_id: userId, org_id: orgId, title })
    .select("id, title")
    .single();

  if (error || !data) {
    safeError("[chat_thread POST]", error);
    return Response.json({ error: "Database error" }, { status: 500 });
  }

  await invalidateUserThreadList(userId);
  return Response.json({ id: data.id, title: data.title });
}
