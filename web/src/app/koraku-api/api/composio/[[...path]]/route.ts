import type { NextRequest } from "next/server";
import { applySupabaseBearerFromCookies } from "@/lib/supabase/proxy-auth";
import { safeUpstreamFetch } from "@/lib/proxy-fetch";

const backend = (process.env.KORAKU_BACKEND_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RouteCtx = { params: Promise<{ path?: string[] }> };

function upstreamUrl(path: string[] | undefined, search: string): string {
  const tail = path?.length ? `/${path.join("/")}` : "";
  return `${backend}/api/composio${tail}${search}`;
}

async function proxy(req: NextRequest, path: string[] | undefined): Promise<Response> {
  const url = upstreamUrl(path, req.nextUrl.search);
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
    method: req.method,
    headers,
    cache: "no-store",
    signal: req.signal,
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
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

export async function GET(req: NextRequest, ctx: RouteCtx) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function POST(req: NextRequest, ctx: RouteCtx) {
  const { path } = await ctx.params;
  return proxy(req, path);
}
