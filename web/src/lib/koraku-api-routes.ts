/**
 * Next.js App Router handlers for ``/koraku-api/*`` BFF proxies.
 *
 * Each mount is a named handler bundle (``automations``, ``composio``, …).
 * Route files under ``src/app/koraku-api`` re-export the bundle they need.
 */
import type { NextRequest } from "next/server";
import {
  type KorakuProxyAuthMode,
  korakuUpstreamUrl,
  proxyKorakuBackend,
  proxyKorakuJson,
  proxyKorakuSse,
} from "@/lib/koraku-backend-proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE" | "HEAD";
type CatchAllCtx = { params: Promise<{ path?: string[] }> };
type CatchAllHandler = (req: NextRequest, ctx: CatchAllCtx) => Promise<Response>;
type FixedHandler = (req: NextRequest) => Promise<Response>;

type CatchAllProxyConfig<M extends HttpMethod = HttpMethod> = {
  upstreamPath: string;
  methods: readonly M[];
  maxDuration?: number;
  /** ``optional`` for inbound webhooks; default ``required`` (401 without Supabase session). */
  authMode?: KorakuProxyAuthMode;
};

type FixedProxyConfig<M extends HttpMethod = HttpMethod> = {
  upstreamPath: string;
  methods: readonly M[];
  authMode?: KorakuProxyAuthMode;
};

type CatchAllProxyBundle<M extends HttpMethod> = {
  runtime: typeof runtime;
  dynamic: typeof dynamic;
  maxDuration?: number;
} & Record<M, CatchAllHandler>;

type FixedProxyBundle<M extends HttpMethod> = {
  runtime: typeof runtime;
  dynamic: typeof dynamic;
} & Record<M, FixedHandler>;

function createCatchAllHandler(
  upstreamPath: string,
  authMode: KorakuProxyAuthMode = "required",
): CatchAllHandler {
  return async function handle(req: NextRequest, ctx: CatchAllCtx): Promise<Response> {
    const { path } = await ctx.params;
    const url = korakuUpstreamUrl(upstreamPath, path, req.nextUrl.search);
    return proxyKorakuBackend(req, url, authMode);
  };
}

export function createKorakuCatchAllProxy<M extends HttpMethod>(
  config: CatchAllProxyConfig<M>,
): CatchAllProxyBundle<M> {
  const handle = createCatchAllHandler(config.upstreamPath, config.authMode ?? "required");
  const methodHandlers = Object.fromEntries(
    config.methods.map((method) => [method, handle]),
  ) as Pick<CatchAllProxyBundle<M>, M>;
  return {
    runtime,
    dynamic,
    ...(config.maxDuration != null ? { maxDuration: config.maxDuration } : {}),
    ...methodHandlers,
  };
}

function createFixedHandler(
  upstreamPath: string,
  authMode: KorakuProxyAuthMode = "required",
): FixedHandler {
  return async function handle(req: NextRequest): Promise<Response> {
    const url = korakuUpstreamUrl(upstreamPath, undefined, req.nextUrl.search);
    return proxyKorakuBackend(req, url, authMode);
  };
}

export function createKorakuFixedProxy<M extends HttpMethod>(
  config: FixedProxyConfig<M>,
): FixedProxyBundle<M> {
  const handle = createFixedHandler(config.upstreamPath, config.authMode ?? "required");
  const methodHandlers = Object.fromEntries(
    config.methods.map((method) => [method, handle]),
  ) as Pick<FixedProxyBundle<M>, M>;
  return {
    runtime,
    dynamic,
    ...methodHandlers,
  };
}

// --- Catch-all mounts ---

export const automations = createKorakuCatchAllProxy({
  upstreamPath: "/api/automations",
  methods: ["GET", "POST", "PATCH", "DELETE"] as const,
  maxDuration: 300,
});

/** POST inbound webhooks for event-triggered automations (token header/query, no session). */
export const automationEvents = createKorakuCatchAllProxy({
  upstreamPath: "/api/automation-events",
  methods: ["POST"] as const,
  maxDuration: 300,
  authMode: "optional",
});

export const composio = createKorakuCatchAllProxy({
  upstreamPath: "/api/composio",
  methods: ["GET", "POST"] as const,
});

export const workspace = createKorakuCatchAllProxy({
  upstreamPath: "/api/workspace",
  methods: ["GET", "POST"] as const,
});

export const sendblue = createKorakuCatchAllProxy({
  upstreamPath: "/sendblue",
  methods: ["GET", "POST"] as const,
  authMode: "optional",
});

// --- Fixed-path mounts ---

export const personalization = createKorakuFixedProxy({
  upstreamPath: "/api/personalization",
  methods: ["GET", "PUT"] as const,
});

export const memoryGraph = createKorakuFixedProxy({
  upstreamPath: "/api/memory/graph",
  methods: ["GET"] as const,
});

/** GET ``/koraku-api/api/chat-models`` — provider/model catalog for chat UI. */
export async function korakuChatModelsGet(req: NextRequest): Promise<Response> {
  return proxyKorakuJson(req, korakuUpstreamUrl("/api/chat-models"), { method: "GET" });
}

// --- Streaming / detached runs ---

/** POST ``/koraku-api/stream`` — live chat SSE (rewrites buffer SSE chunks). */
export async function korakuStreamPost(req: NextRequest): Promise<Response> {
  const body = await req.text();
  return proxyKorakuSse(req, korakuUpstreamUrl("/stream"), {
    method: "POST",
    body,
    extraHeaders: {
      "Content-Type": req.headers.get("content-type") || "application/json",
    },
  });
}

/** POST ``/koraku-api/runs`` — start detached run; returns ``{ run_id }`` JSON. */
export async function korakuRunsPost(req: NextRequest): Promise<Response> {
  const body = await req.text();
  return proxyKorakuJson(req, korakuUpstreamUrl("/runs"), { method: "POST", body });
}

/** GET ``/koraku-api/runs/:runId/stream`` — detached run SSE tail + replay. */
export async function korakuRunStreamGet(
  req: NextRequest,
  ctx: { params: Promise<{ runId: string }> },
): Promise<Response> {
  const { runId } = await ctx.params;
  const url = new URL(korakuUpstreamUrl(`/runs/${encodeURIComponent(runId)}/stream`));
  const after = req.nextUrl.searchParams.get("after");
  if (after != null && after !== "") {
    url.searchParams.set("after", after);
  }

  return proxyKorakuSse(req, url.toString(), {
    method: "GET",
    mutateHeaders: (headers) => {
      const leid = req.headers.get("last-event-id") || req.headers.get("Last-Event-ID");
      if (leid) {
        headers.set("Last-Event-ID", leid);
      }
    },
  });
}

/** GET ``/koraku-api/runs/:runId/status`` — JSON run state for reconnect. */
export async function korakuRunStatusGet(
  req: NextRequest,
  ctx: { params: Promise<{ runId: string }> },
): Promise<Response> {
  const { runId } = await ctx.params;
  return proxyKorakuJson(req, korakuUpstreamUrl(`/runs/${encodeURIComponent(runId)}/status`), {
    method: "GET",
  });
}
