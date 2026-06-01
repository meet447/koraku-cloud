import type { NextRequest } from "next/server";
import { applySupabaseBearerFromCookies } from "@/lib/supabase/proxy-auth";
import { safeUpstreamFetch } from "@/lib/proxy-fetch";

const backend = (process.env.KORAKU_BACKEND_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** SSE replay + live tail for a detached run (closing this connection does not cancel the run on the backend). */
export async function GET(
  req: NextRequest,
  ctx: { params: Promise<{ runId: string }> },
) {
  const { runId } = await ctx.params;
  const headers = new Headers({
    Accept: "text/event-stream",
  });
  const auth = req.headers.get("authorization");
  if (auth) {
    headers.set("Authorization", auth);
  }
  await applySupabaseBearerFromCookies(headers);

  const leid = req.headers.get("last-event-id") || req.headers.get("Last-Event-ID");
  if (leid) {
    headers.set("Last-Event-ID", leid);
  }

  const url = new URL(`${backend}/runs/${encodeURIComponent(runId)}/stream`);
  const after = req.nextUrl.searchParams.get("after");
  if (after != null && after !== "") {
    url.searchParams.set("after", after);
  }

  const upstream = await safeUpstreamFetch(
    url.toString(),
    { method: "GET", headers, cache: "no-store", signal: req.signal },
    "sse",
  );
  if (upstream.status === 502 || upstream.status === 499) return upstream;

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
