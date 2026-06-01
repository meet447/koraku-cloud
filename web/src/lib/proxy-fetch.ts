const SSE_HEADERS: HeadersInit = {
  "Content-Type": "text/event-stream; charset=utf-8",
  "Cache-Control": "no-cache, no-transform",
  Connection: "keep-alive",
  "X-Accel-Buffering": "no",
};

const JSON_HEADERS: HeadersInit = {
  "Content-Type": "application/json",
};

function isAbortError(e: unknown): boolean {
  return e instanceof Error && (e.name === "AbortError" || e.name === "DOMException");
}

export function sseUpstreamErrorResponse(message: string): Response {
  const body =
    `event: error\ndata: ${JSON.stringify({ error: message, code: "upstream_unavailable" })}\n\n` +
    `event: done\n\n`;
  return new Response(body, { status: 502, headers: SSE_HEADERS });
}

export function jsonUpstreamErrorResponse(message: string): Response {
  return new Response(
    JSON.stringify({ error: message, code: "upstream_unavailable" }),
    { status: 502, headers: JSON_HEADERS },
  );
}

export function clientAbortedResponse(): Response {
  return new Response(null, { status: 499 });
}

type FetchKind = "sse" | "json";

export async function safeUpstreamFetch(
  url: string,
  init: RequestInit,
  kind: FetchKind,
): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch (e) {
    if (isAbortError(e)) return clientAbortedResponse();
    const msg = e instanceof Error ? e.message : "Backend unavailable";
    return kind === "sse"
      ? sseUpstreamErrorResponse(msg)
      : jsonUpstreamErrorResponse(msg);
  }
}
