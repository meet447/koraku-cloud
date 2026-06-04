import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import {
  applyKorakuSseEvent,
  initialRunState,
  parseKorakuEventInner,
  type RunState,
  type TurnStreamStatus,
} from "@/lib/korakuReducer";
import type { ChatMessage, StreamingTurn } from "@/lib/koraku-chat/types";

export function parseSseBlock(raw: string): { event: string; data: string; id?: string } {
  let event = "message";
  let id: string | undefined;
  const dataLines: string[] = [];
  for (const line of raw.split("\n")) {
    const L = line.replace(/\r$/, "");
    if (L.startsWith("event:")) event = L.slice(6).trim();
    else if (L.startsWith("id:")) id = L.slice(3).trim();
    else if (L.startsWith("data:")) dataLines.push(L.slice(5).trimStart());
  }
  return { event, data: dataLines.join("\n"), id };
}

export function collectStreamingTurns(
  sessionList: { id: string }[],
  messagesBySession: Record<string, ChatMessage[]>,
): StreamingTurn[] {
  const out: StreamingTurn[] = [];
  const seen = new Set<string>();
  for (const s of sessionList) {
    for (const m of messagesBySession[s.id] ?? []) {
      if (m.role !== "assistant") continue;
      if (m.run.streamStatus !== "streaming") continue;
      const turnId = (m.run.turnId || m.run.runId || m.id).trim();
      if (!turnId || seen.has(turnId)) continue;
      seen.add(turnId);
      out.push({
        threadId: s.id,
        assistantMsgId: m.id,
        turnId,
        startedAt: m.run.streamStartedAt ?? 0,
      });
    }
  }
  return out;
}

export function runStateForStreamReplay(prev: RunState): RunState {
  return {
    ...initialRunState(),
    turnId: prev.turnId,
    runId: prev.runId || prev.turnId,
    streamStatus: "streaming",
    sseAfter: -1,
    streamStartedAt: prev.streamStartedAt,
    dropdownModelLabel: prev.dropdownModelLabel,
    statusText: "Reconnecting…",
  };
}

export function finalizeTurnStreamStatus(error: string | null, completed: boolean): TurnStreamStatus {
  if (!completed) return "streaming";
  return error?.trim() ? "failed" : "completed";
}

export function rememberServerChatSession(
  uiSessionId: string,
  payload: Record<string, unknown>,
  mapRef: MutableRefObject<Record<string, string>>,
) {
  const t = String(payload.type || "");
  if (t === "koraku.started") {
    const d = payload.data as Record<string, unknown> | undefined;
    const id = d?.chatSessionId;
    if (typeof id === "string" && id.length > 8) mapRef.current[uiSessionId] = id;
    return;
  }
  if (t === "agent.mode") {
    const d = payload.data as Record<string, unknown> | undefined;
    const id = d?.session_id;
    if (typeof id === "string" && id.length > 8) mapRef.current[uiSessionId] = id;
    return;
  }
  if (t === "koraku.event") {
    const inner = parseKorakuEventInner(payload.data);
    if (
      inner &&
      inner.type === "koraku.trace" &&
      inner.trace === "mode" &&
      inner.data &&
      typeof inner.data === "object"
    ) {
      const id = (inner.data as Record<string, unknown>).session_id;
      if (typeof id === "string" && id.length > 8) mapRef.current[uiSessionId] = id;
    }
  }
}

/** Read SSE chunks from a detached-run subscribe response and apply Koraku payloads. */
export async function ingestKorakuSseFromReader(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  opts: {
    sessionId: string;
    assistantMsgId: string;
    runId: string | null;
    serverChatSessionRef: MutableRefObject<Record<string, string>>;
    setServerChatSessionByUi: Dispatch<SetStateAction<Record<string, string>>>;
    updateAssistantRun: (
      sessionId: string,
      assistantMessageId: string,
      updater: (r: RunState) => RunState,
    ) => void;
    onSseAfter?: (after: number) => void;
  },
): Promise<boolean> {
  const decoder = new TextDecoder();
  let buffer = "";
  let sawDoneEvent = false;
  const {
    sessionId: sid,
    assistantMsgId,
    runId,
    serverChatSessionRef,
    setServerChatSessionByUi,
    updateAssistantRun,
    onSseAfter,
  } = opts;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const payloads: Record<string, unknown>[] = [];
    let sawStreamDone = false;
    for (;;) {
      const sepRn = buffer.indexOf("\r\n\r\n");
      const sepN = buffer.indexOf("\n\n");
      let sep = -1;
      let skip = 0;
      if (sepRn !== -1 && (sepN === -1 || sepRn <= sepN)) {
        sep = sepRn;
        skip = 4;
      } else if (sepN !== -1) {
        sep = sepN;
        skip = 2;
      }
      if (sep === -1) break;
      const rawBlock = buffer.slice(0, sep);
      buffer = buffer.slice(sep + skip);
      const { event, data, id } = parseSseBlock(rawBlock);
      if (event === "done") {
        sawStreamDone = true;
        sawDoneEvent = true;
        break;
      }
      if (event === "ping") continue;
      if (runId && id && /^\d+$/.test(id)) {
        onSseAfter?.(Number(id));
      }
      if (!data) continue;
      try {
        payloads.push(JSON.parse(data) as Record<string, unknown>);
      } catch {
        continue;
      }
    }
    if (payloads.length > 0) {
      for (const payload of payloads) {
        rememberServerChatSession(sid, payload, serverChatSessionRef);
      }
      const mapped = serverChatSessionRef.current[sid]?.trim();
      if (mapped) {
        setServerChatSessionByUi((prev) =>
          prev[sid] === mapped ? prev : { ...prev, [sid]: mapped },
        );
      }
      updateAssistantRun(sid, assistantMsgId, (r) =>
        payloads.reduce<RunState>(
          (acc, p) => applyKorakuSseEvent(acc, p),
          r,
        ),
      );
    }
    if (sawStreamDone) {
      return true;
    }
  }
  return sawDoneEvent;
}
