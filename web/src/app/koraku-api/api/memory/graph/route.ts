import type { NextRequest } from "next/server";
import { applySupabaseBearerFromCookies } from "@/lib/supabase/proxy-auth";
import { applyTenantHeadersFromCookies } from "@/lib/tenant/server";
import { safeUpstreamFetch } from "@/lib/proxy-fetch";

const backend = (process.env.KORAKU_BACKEND_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const search = req.nextUrl.search || "";
  const url = `${backend}/api/memory/graph${search}`;
  const headers = new Headers();
  const skip = new Set([
    "connection",
    "keep-alive",
    "transfer-encoding",
    "te",
    "trailer",
    "upgrade",
    "host",
    "content-length",
  ]);
  req.headers.forEach((value, key) => {
    if (!skip.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });

  await applySupabaseBearerFromCookies(headers);
  await applyTenantHeadersFromCookies(headers);

  const upstream = await safeUpstreamFetch(
    url,
    { method: "GET", headers, cache: "no-store", signal: req.signal },
    "json",
  );
  if (upstream.status === 502 || upstream.status === 499) return upstream;
  const outHeaders = new Headers();
  const ct = upstream.headers.get("content-type");
  if (ct) outHeaders.set("Content-Type", ct);
  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: outHeaders,
  });
}
