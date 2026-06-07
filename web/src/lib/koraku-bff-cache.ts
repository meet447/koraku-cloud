import type { NextRequest } from "next/server";
import { getCachedJson, setCachedJson, userBffCacheKey } from "@/lib/koraku-redis";
import { getSessionUserIdFromCookies, proxyUnauthorizedResponse } from "@/lib/supabase/proxy-auth";
import { korakuUpstreamUrl, proxyKorakuBackend, proxyKorakuJson } from "@/lib/koraku-backend-proxy";

type CachedProxyBody = {
  status: number;
  contentType: string;
  body: string;
};

const CHAT_MODELS_TTL_SEC = 120;
const PERSONALIZATION_TTL_SEC = 60;

/** GET upstream JSON with per-user Redis cache (skips Python on cache hit). */
export async function proxyKorakuJsonGetCached(
  req: NextRequest,
  upstreamPath: string,
  scope: string,
  ttlSec: number,
): Promise<Response> {
  const userId = await getSessionUserIdFromCookies();
  if (!userId) {
    return proxyUnauthorizedResponse();
  }

  const cacheKey = userBffCacheKey(scope, userId);
  const cached = await getCachedJson<CachedProxyBody>(cacheKey);
  if (cached) {
    return new Response(cached.body, {
      status: cached.status,
      headers: { "Content-Type": cached.contentType },
    });
  }

  const url = korakuUpstreamUrl(upstreamPath, undefined, req.nextUrl.search);
  const upstream = await proxyKorakuJson(req, url, { method: "GET" });
  if (!upstream.ok) {
    return upstream;
  }

  const body = await upstream.text();
  const contentType = upstream.headers.get("content-type") || "application/json";
  await setCachedJson(cacheKey, { status: upstream.status, contentType, body }, ttlSec);
  return new Response(body, {
    status: upstream.status,
    headers: { "Content-Type": contentType },
  });
}

export async function korakuChatModelsGetCached(req: NextRequest): Promise<Response> {
  return proxyKorakuJsonGetCached(req, "/api/chat-models", "chat-models", CHAT_MODELS_TTL_SEC);
}

export async function korakuPersonalizationGetCached(req: NextRequest): Promise<Response> {
  return proxyKorakuJsonGetCached(
    req,
    "/api/personalization",
    "personalization",
    PERSONALIZATION_TTL_SEC,
  );
}

export async function korakuPersonalizationPut(req: NextRequest): Promise<Response> {
  const userId = await getSessionUserIdFromCookies();
  const url = korakuUpstreamUrl("/api/personalization", undefined, req.nextUrl.search);
  const upstream = await proxyKorakuBackend(req, url);
  if (userId && upstream.ok) {
    const { invalidateUserBffCache } = await import("@/lib/koraku-redis");
    await invalidateUserBffCache("personalization", userId);
  }
  return upstream;
}
