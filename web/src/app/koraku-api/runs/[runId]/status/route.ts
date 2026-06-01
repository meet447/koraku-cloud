import type { NextRequest } from "next/server";
import { applySupabaseBearerFromCookies } from "@/lib/supabase/proxy-auth";
import { safeUpstreamFetch } from "@/lib/proxy-fetch";

const backend = (process.env.KORAKU_BACKEND_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** JSON run state for reconnect / mobile (same worker as the run). */
export async function GET(
  req: NextRequest,
  ctx: { params: Promise<{ runId: string }> },
) {
  const { runId } = await ctx.params;
  const headers = new Headers({ Accept: "application/json" });
  const auth = req.headers.get("authorization");
  if (auth) headers.set("Authorization", auth);
  await applySupabaseBearerFromCookies(headers);

  const upstream = await safeUpstreamFetch(
    `${backend}/runs/${encodeURIComponent(runId)}/status`,
    { method: "GET", headers, cache: "no-store", signal: req.signal },
    "json",
  );
  if (upstream.status === 502 || upstream.status === 499) return upstream;
  const ct = upstream.headers.get("content-type") || "application/json";
  return new Response(upstream.body, {
    status: upstream.status,
    headers: { "Content-Type": ct },
  });
}
