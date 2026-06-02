import type { NextRequest } from "next/server";
import { applySupabaseBearerFromCookies } from "@/lib/supabase/proxy-auth";
import {
  KORAKU_SSE_RESPONSE_HEADERS,
  safeUpstreamFetch,
} from "@/lib/proxy-fetch";

export const korakuBackendBase = (process.env.KORAKU_BACKEND_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "transfer-encoding",
  "te",
  "trailer",
  "upgrade",
  "host",
  "content-length",
]);

type UpstreamKind = "json" | "sse" | "body";

/** Copy safe inbound headers from the browser request (hop-by-hop headers omitted). */
export function copyInboundHeaders(req: NextRequest, target: Headers): void {
  req.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      target.set(key, value);
    }
  });
}

/** Auth + org (cookies) + optional client Authorization / X-Request-ID. */
export async function buildKorakuProxyHeaders(
  req: NextRequest,
  extra?: HeadersInit,
): Promise<Headers> {
  const headers = new Headers();
  copyInboundHeaders(req, headers);
  const auth = req.headers.get("authorization");
  if (auth) {
    headers.set("Authorization", auth);
  }
  const rid = req.headers.get("x-request-id");
  if (rid) {
    headers.set("X-Request-ID", rid);
  }
  await applySupabaseBearerFromCookies(headers);
  if (extra) {
    new Headers(extra).forEach((value, key) => headers.set(key, value));
  }
  return headers;
}

/** Build a Koraku Python API URL under ``korakuBackendBase``. */
export function korakuUpstreamUrl(
  upstreamPath: string,
  pathSegments?: string[],
  search = "",
): string {
  const base = upstreamPath.startsWith("/") ? upstreamPath : `/${upstreamPath}`;
  const tail = pathSegments?.length ? `/${pathSegments.join("/")}` : "";
  return `${korakuBackendBase}${base}${tail}${search}`;
}

export function isUpstreamGatewayError(status: number): boolean {
  return status === 502 || status === 499;
}

/** Forward an upstream ``fetch`` response to the browser without buffering the body. */
export function passthroughUpstreamResponse(upstream: Response, kind: UpstreamKind): Response {
  if (isUpstreamGatewayError(upstream.status)) {
    return upstream;
  }
  if (kind === "sse") {
    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: KORAKU_SSE_RESPONSE_HEADERS,
    });
  }
  if (kind === "json") {
    const ct = upstream.headers.get("content-type") || "application/json";
    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: { "Content-Type": ct },
    });
  }
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

/** Proxy a request to the Koraku Python API (JSON, files, etc.). */
export async function proxyKorakuBackend(
  req: NextRequest,
  upstreamUrl: string,
): Promise<Response> {
  const headers = await buildKorakuProxyHeaders(req);

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

  const upstream = await safeUpstreamFetch(upstreamUrl, init, "json");
  return passthroughUpstreamResponse(upstream, "body");
}

/** Proxy an SSE GET/POST to the backend (streaming body, anti-buffer headers). */
export async function proxyKorakuSse(
  req: NextRequest,
  upstreamUrl: string,
  init: {
    method: "GET" | "POST";
    body?: string;
    extraHeaders?: HeadersInit;
    mutateHeaders?: (headers: Headers) => void;
  },
): Promise<Response> {
  const headers = await buildKorakuProxyHeaders(req, { Accept: "text/event-stream" });
  if (init.extraHeaders) {
    new Headers(init.extraHeaders).forEach((value, key) => headers.set(key, value));
  }
  init.mutateHeaders?.(headers);
  const upstream = await safeUpstreamFetch(
    upstreamUrl,
    {
      method: init.method,
      headers,
      body: init.body,
      cache: "no-store",
      signal: req.signal,
    },
    "sse",
  );
  return passthroughUpstreamResponse(upstream, "sse");
}

/** Proxy a JSON request with an optional text body (e.g. detached run start). */
export async function proxyKorakuJson(
  req: NextRequest,
  upstreamUrl: string,
  init: { method: "GET" | "POST"; body?: string },
): Promise<Response> {
  const headers = await buildKorakuProxyHeaders(req, {
    Accept: "application/json",
    ...(init.body
      ? { "Content-Type": req.headers.get("content-type") || "application/json" }
      : {}),
  });
  const upstream = await safeUpstreamFetch(
    upstreamUrl,
    {
      method: init.method,
      headers,
      body: init.body,
      cache: "no-store",
      signal: req.signal,
    },
    "json",
  );
  return passthroughUpstreamResponse(upstream, "json");
}
