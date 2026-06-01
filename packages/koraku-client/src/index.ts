/** Koraku SSE outer event (FastAPI ``text/event-stream``). */
export type KorakuOuterEvent = {
  type: string;
  data?: unknown;
  [key: string]: unknown;
};

export type StreamChatOptions = {
  baseUrl: string;
  message: string;
  sessionId?: string;
  model?: string;
  provider?: string;
  executionTarget?: "cloud" | "local" | "server";
  headers?: Record<string, string>;
  signal?: AbortSignal;
};

/** Parse ``koraku.event`` ``data`` (JSON string or object). */
export function parseKorakuEventInner(raw: unknown): Record<string, unknown> | null {
  if (!raw) return null;
  if (typeof raw === "object") return raw as Record<string, unknown>;
  if (typeof raw === "string") {
    try {
      return JSON.parse(raw) as Record<string, unknown>;
    } catch {
      return null;
    }
  }
  return null;
}

/** Parse one SSE ``data:`` line into a Koraku outer event object. */
export function parseSseDataLine(line: string): KorakuOuterEvent | null {
  const trimmed = line.trim();
  if (!trimmed.startsWith("data:")) return null;
  const payload = trimmed.slice(5).trim();
  if (!payload || payload === "[DONE]") return null;
  try {
    return JSON.parse(payload) as KorakuOuterEvent;
  } catch {
    return null;
  }
}

/**
 * Stream a chat turn from ``POST /stream``.
 * Yields parsed outer SSE events (`koraku.started`, `koraku.event`, …).
 */
export async function* streamChat(
  options: StreamChatOptions,
): AsyncGenerator<KorakuOuterEvent, void, unknown> {
  const url = `${options.baseUrl.replace(/\/$/, "")}/stream`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...(options.headers ?? {}),
    },
    body: JSON.stringify({
      msg: options.message,
      session_id: options.sessionId ?? "",
      model: options.model ?? "",
      provider: options.provider ?? "",
      execution_target: options.executionTarget ?? "cloud",
    }),
    signal: options.signal,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Koraku stream failed (${res.status}): ${text || res.statusText}`);
  }
  if (!res.body) {
    throw new Error("Koraku stream response has no body");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        const event = parseSseDataLine(line);
        if (event) yield event;
      }
    }
    if (buffer.trim()) {
      const event = parseSseDataLine(buffer);
      if (event) yield event;
    }
  } finally {
    reader.releaseLock();
  }
}

export class KorakuClient {
  constructor(
    private readonly baseUrl: string,
    private readonly defaultHeaders: Record<string, string> = {},
  ) {}

  streamChat(
    message: string,
    options: Omit<StreamChatOptions, "baseUrl" | "message"> = {},
  ): AsyncGenerator<KorakuOuterEvent, void, unknown> {
    return streamChat({
      baseUrl: this.baseUrl,
      message,
      headers: { ...this.defaultHeaders, ...(options.headers ?? {}) },
      ...options,
    });
  }

  /** Collect inner events from ``koraku.event`` payloads for simple integrations. */
  async *streamInnerEvents(
    message: string,
    options: Omit<StreamChatOptions, "baseUrl" | "message"> = {},
  ): AsyncGenerator<Record<string, unknown>, void, unknown> {
    for await (const outer of this.streamChat(message, options)) {
      if (outer.type === "koraku.event") {
        const inner = parseKorakuEventInner(outer.data);
        if (inner) yield inner;
      }
    }
  }
}
