import type { NextRequest } from "next/server";
import { applySupabaseBearerFromCookies } from "@/lib/supabase/proxy-auth";
import { safeUpstreamFetch } from "@/lib/proxy-fetch";

const backend = (process.env.KORAKU_BACKEND_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

async function proxy(req: NextRequest, method: "GET" | "PUT"): Promise<Response> {
  const url = `${backend}/api/personalization`;
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

  const init: RequestInit = {
    method,
    headers,
    cache: "no-store",
    signal: req.signal,
  };

  if (method === "PUT") {
    const buf = await req.arrayBuffer();
    if (buf.byteLength > 0) {
      init.body = buf;
    } else {
      headers.delete("content-type");
    }
  }

  const upstream = await safeUpstreamFetch(url, init, "json");
  if (upstream.status === 502 || upstream.status === 499) return upstream;
  const outHeaders = new Headers();
  const ct = upstream.headers.get("content-type");
  if (ct) {
    outHeaders.set("Content-Type", ct);
  }
  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: outHeaders,
  });
}

export async function GET(req: NextRequest) {
  return proxy(req, "GET");
}

export async function PUT(req: NextRequest) {
  return proxy(req, "PUT");
}
