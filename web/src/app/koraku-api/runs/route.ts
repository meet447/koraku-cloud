import type { NextRequest } from "next/server";
import { applySupabaseBearerFromCookies } from "@/lib/supabase/proxy-auth";
import { safeUpstreamFetch } from "@/lib/proxy-fetch";

const backend = (process.env.KORAKU_BACKEND_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** Start a detached agent run; returns JSON ``{ run_id }``. Subscribe via GET ``/koraku-api/runs/:id/stream``. */
export async function POST(req: NextRequest) {
  const body = await req.text();
  const headers = new Headers({
    "Content-Type": req.headers.get("content-type") || "application/json",
    Accept: "application/json",
  });
  const auth = req.headers.get("authorization");
  if (auth) {
    headers.set("Authorization", auth);
  }
  await applySupabaseBearerFromCookies(headers);

  const upstream = await safeUpstreamFetch(
    `${backend}/runs`,
    { method: "POST", headers, body, cache: "no-store", signal: req.signal },
    "json",
  );
  if (upstream.status === 502 || upstream.status === 499) return upstream;

  const ct = upstream.headers.get("content-type") || "application/json";
  return new Response(upstream.body, {
    status: upstream.status,
    headers: { "Content-Type": ct },
  });
}
