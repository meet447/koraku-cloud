"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type Dispatch,
  type MutableRefObject,
  type SetStateAction,
} from "react";
import {
  applyKorakuSseEvent,
  initialRunState,
  parseKorakuEventInner,
  type RunState,
  type TurnStreamStatus,
} from "@/lib/korakuReducer";
import type { ComposerImage } from "@/components/Composer";
import type { QueuedMessagePreview } from "@/components/MessageQueueBar";
import { createBrowserSupabaseClient } from "@/lib/supabase/browser";

export type ChatMessage =
  | {
      id: string;
      role: "user";
      text: string;
      images?: { id: string; previewUrl: string }[];
    }
  | { id: string; role: "assistant"; run: RunState };

/** Max agent streams open at once across all sidebar threads. */
export const MAX_CONCURRENT_CHAT_STREAMS = 3;

const CLIENT_HISTORY_MAX_MESSAGES = 24;
const CLIENT_HISTORY_MAX_TEXT_CHARS = 8_000;

/**
 * Detached streaming (``POST /runs`` + ``GET /runs/:id/stream``) for tab-close resume on the same API worker.
 *
 * ``NEXT_PUBLIC_KORAKU_DETACHED_CHAT``:
 * - ``off`` / ``0`` — inline ``POST /stream`` only (lowest latency; refresh aborts the turn).
 * - ``1`` / ``true`` / ``always`` — every chat turn uses detached runs.
 * - ``heavy`` / ``long`` / ``auto`` — detached only for long text (≥3200 chars) or any inline images.
 * - empty (default) — detached for signed-in persisted chats; inline for local-only guests.
 */
type DetachedChatMode = "default" | "off" | "always" | "heavy";

function detachedChatMode(): DetachedChatMode {
  const v = (process.env.NEXT_PUBLIC_KORAKU_DETACHED_CHAT ?? "").trim().toLowerCase();
  if (v === "off" || v === "0" || v === "false") return "off";
  if (v === "1" || v === "true" || v === "yes" || v === "always") return "always";
  if (v === "heavy" || v === "long" || v === "auto") return "heavy";
  return "default";
}

function shouldUseDetachedStreamingForPayload(
  textLen: number,
  imageCount: number,
  persistenceEnabled: boolean,
): boolean {
  const mode = detachedChatMode();
  if (mode === "always") return true;
  if (mode === "heavy") {
    return textLen >= 3200 || imageCount > 0;
  }
  if (mode === "off") return false;
  // Unset env: signed-in persisted chats use detached runs so refresh can reconnect.
  return persistenceEnabled;
}

async function fetchDetachedRunStatusJson(
  runId: string,
  authHeaders: Record<string, string>,
): Promise<{ state?: string; hint?: string } | null> {
  try {
    const r = await fetch(`/koraku-api/runs/${encodeURIComponent(runId)}/status`, {
      method: "GET",
      headers: { Accept: "application/json", ...authHeaders },
    });
    if (!r.ok) return null;
    return (await r.json()) as { state?: string; hint?: string };
  } catch {
    return null;
  }
}

const EMPTY_THREAD_MESSAGES: ChatMessage[] = [];

export type ChatSession = { id: string; title: string };

export type OutboundJob = {
  id: string;
  text: string;
  provider: string;
  model: string;
  dropdownModelLabel: string;
  images: ComposerImage[];
};

function uid(): string {
  return crypto.randomUUID();
}

function parseSseBlock(raw: string): { event: string; data: string; id?: string } {
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

type StreamingTurn = {
  threadId: string;
  assistantMsgId: string;
  turnId: string;
  after: number;
};

/** In-flight detached turns persisted on assistant rows (``streamStatus: streaming``). */
function collectStreamingTurns(
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
        after: typeof m.run.sseAfter === "number" ? m.run.sseAfter : -1,
      });
    }
  }
  return out;
}

function finalizeTurnStreamStatus(error: string | null, completed: boolean): TurnStreamStatus {
  if (!completed) return "streaming";
  return error?.trim() ? "failed" : "completed";
}

/** Read SSE chunks from a detached-run subscribe response and apply Koraku payloads. */
async function ingestKorakuSseFromReader(
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

function jobPreviewText(job: OutboundJob): string {
  const t = job.text.trim();
  if (t) {
    return t.length > 120 ? `${t.slice(0, 117)}…` : t;
  }
  if (job.images.length > 1) return `${job.images.length} images`;
  if (job.images.length === 1) return "Image";
  return "…";
}

function rememberServerChatSession(
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

function deserializeRunState(raw: unknown): RunState {
  const b = initialRunState();
  if (!raw || typeof raw !== "object") return b;
  const o = raw as Partial<RunState>;
  return {
    ...b,
    ...o,
    timeline: Array.isArray(o.timeline) ? o.timeline : b.timeline,
    pendingToolByUseId:
      o.pendingToolByUseId && typeof o.pendingToolByUseId === "object"
        ? o.pendingToolByUseId
        : b.pendingToolByUseId,
    blockKindByIndex:
      o.blockKindByIndex && typeof o.blockKindByIndex === "object"
        ? o.blockKindByIndex
        : b.blockKindByIndex,
    blockNameByIndex:
      o.blockNameByIndex && typeof o.blockNameByIndex === "object"
        ? o.blockNameByIndex
        : b.blockNameByIndex,
    partialJsonByIndex:
      o.partialJsonByIndex && typeof o.partialJsonByIndex === "object"
        ? o.partialJsonByIndex
        : b.partialJsonByIndex,
    sawToolUseThisTurn:
      typeof o.sawToolUseThisTurn === "boolean" ? o.sawToolUseThisTurn : b.sawToolUseThisTurn,
    assistantBubbleMode:
      o.assistantBubbleMode === "step" || o.assistantBubbleMode === "final"
        ? o.assistantBubbleMode
        : b.assistantBubbleMode,
    stepCaption: typeof o.stepCaption === "string" ? o.stepCaption : b.stepCaption,
    turnId: typeof o.turnId === "string" ? o.turnId : b.turnId,
    streamStatus:
      o.streamStatus === "streaming" ||
      o.streamStatus === "completed" ||
      o.streamStatus === "failed"
        ? o.streamStatus
        : b.streamStatus,
    sseAfter: typeof o.sseAfter === "number" ? o.sseAfter : b.sseAfter,
  };
}

function apiRowToChatMessage(row: {
  id: string;
  role: string;
  contentJson: unknown;
}): ChatMessage | null {
  const c = row.contentJson;
  if (row.role === "user") {
    if (!c || typeof c !== "object") {
      return { id: row.id, role: "user", text: "" };
    }
    const o = c as Record<string, unknown>;
    const text = typeof o.text === "string" ? o.text : "";
    let images: { id: string; previewUrl: string }[] | undefined;
    if (Array.isArray(o.images)) {
      images = o.images
        .map((x) => {
          if (!x || typeof x !== "object") return null;
          const im = x as Record<string, unknown>;
          const id = typeof im.id === "string" ? im.id : uid();
          const previewUrl = typeof im.previewUrl === "string" ? im.previewUrl : "";
          return previewUrl ? { id, previewUrl } : null;
        })
        .filter((x): x is { id: string; previewUrl: string } => x != null);
    }
    return { id: row.id, role: "user", text, images: images?.length ? images : undefined };
  }
  if (row.role === "assistant") {
    const runRaw =
      c && typeof c === "object" && "run" in (c as object)
        ? (c as { run: unknown }).run
        : c;
    const run = deserializeRunState(runRaw);
    if (!run.turnId) {
      run.turnId = run.runId || row.id;
    }
    if (!run.runId && run.turnId) {
      run.runId = run.turnId;
    }
    return { id: row.id, role: "assistant", run };
  }
  return null;
}

/** Omit empty completed assistant rows; keep in-flight turns for DB resume. */
function messagesReadyToPersist(msgs: ChatMessage[]): ChatMessage[] {
  return msgs.filter((m) => {
    if (m.role !== "assistant") return true;
    if (m.run.streamStatus === "streaming") return true;
    return Boolean(m.run.assistantMarkdown.trim() || m.run.error?.trim());
  });
}

function chatMessageToApiRow(m: ChatMessage): {
  id: string;
  role: string;
  contentJson: unknown;
} {
  if (m.role === "user") {
    const images = m.images?.map(({ id, previewUrl }) => ({
      id,
      previewUrl: previewUrl.length < 48_000 ? previewUrl : "",
    }));
    return {
      id: m.id,
      role: "user",
      contentJson: {
        text: m.text,
        ...(images?.some((i) => i.previewUrl) ? { images } : {}),
      },
    };
  }
  return { id: m.id, role: "assistant", contentJson: { run: m.run } };
}

function chatMessagesToClientHistory(messages: ChatMessage[]): {
  role: "user" | "assistant";
  text: string;
}[] {
  return messages
    .slice(-CLIENT_HISTORY_MAX_MESSAGES)
    .map((m) => {
      const text = m.role === "user" ? m.text : m.run.assistantMarkdown;
      const clean = text.trim();
      if (!clean) return null;
      return {
        role: m.role,
        text:
          clean.length > CLIENT_HISTORY_MAX_TEXT_CHARS
            ? `${clean.slice(0, CLIENT_HISTORY_MAX_TEXT_CHARS - 1)}…`
            : clean,
      };
    })
    .filter((m): m is { role: "user" | "assistant"; text: string } => m != null);
}

export function useKorakuChat() {
  const [hydrated, setHydrated] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeId, setActiveId] = useState("");
  const [messagesBySession, setMessagesBySession] = useState<
    Record<string, ChatMessage[]>
  >({});
  /** Session ids with an active POST /stream (for sidebar + composer). */
  const [streamingSessionIds, setStreamingSessionIds] = useState<string[]>([]);
  /** Session ids currently running ``deleteSession`` (sidebar loading). */
  const [deletingSessionIds, setDeletingSessionIds] = useState<string[]>([]);
  /** Session ids waiting on ``GET /messages`` (main column skeleton). */
  const [messagesLoadingSessionIds, setMessagesLoadingSessionIds] = useState<string[]>([]);
  const [queuedMessages, setQueuedMessages] = useState<QueuedMessagePreview[]>([]);
  const streamingSidsRef = useRef<Set<string>>(new Set());
  const abortBySessionRef = useRef<Record<string, AbortController>>({});
  const serverChatSessionRef = useRef<Record<string, string>>({});
  /** UI session id → server chat UUID (for workspace API after first cloud stream). */
  const [serverChatSessionByUi, setServerChatSessionByUi] = useState<
    Record<string, string>
  >({});
  const messagesBySessionRef = useRef<Record<string, ChatMessage[]>>({});
  const persistenceEnabledRef = useRef(false);
  const messagesLoadedForThreadRef = useRef<Set<string>>(new Set());
  /** Prevents duplicate ``/messages`` fetches for the same thread while one is in flight. */
  const messagesLoadInflightRef = useRef<Set<string>>(new Set());
  const activeIdRef = useRef(activeId);
  const sessionsRef = useRef(sessions);
  /** FIFO outbound messages per UI session when that session already has a stream or global cap is hit. */
  const queuesRef = useRef<Record<string, OutboundJob[]>>({});
  const runOutboundJobRef = useRef<(sid: string, job: OutboundJob) => void>(() => {});
  const tryDrainGlobalQueueRef = useRef<() => void>(() => {});
  const newChatInFlightRef = useRef(false);
  /** Dedupe detached-run resume side-effects (Strict Mode / re-renders). */
  const detachResumeStartedRef = useRef<Set<string>>(new Set());
  const persistDebounceRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const resumeStreamingTurnsRef = useRef<() => void>(() => {});

  const messages = messagesBySession[activeId] ?? EMPTY_THREAD_MESSAGES;
  const busy = streamingSessionIds.includes(activeId);

  const markStreamStart = useCallback((sid: string) => {
    streamingSidsRef.current.add(sid);
    setStreamingSessionIds(Array.from(streamingSidsRef.current));
  }, []);

  const markStreamEnd = useCallback((sid: string) => {
    streamingSidsRef.current.delete(sid);
    setStreamingSessionIds(Array.from(streamingSidsRef.current));
  }, []);

  useEffect(() => {
    activeIdRef.current = activeId;
    const q = queuesRef.current[activeId] ?? [];
    setQueuedMessages(q.map((j) => ({ id: j.id, text: jobPreviewText(j) })));
  }, [activeId]);

  useLayoutEffect(() => {
    sessionsRef.current = sessions;
  }, [sessions]);

  useLayoutEffect(() => {
    messagesBySessionRef.current = messagesBySession;
  }, [messagesBySession]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const supabase = createBrowserSupabaseClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (cancelled) return;
        if (!session) {
          const id = uid();
          persistenceEnabledRef.current = false;
          setSessions([{ id, title: "New chat" }]);
          setActiveId(id);
          setMessagesBySession({ [id]: [] });
          messagesLoadedForThreadRef.current = new Set([id]);
          setHydrated(true);
          return;
        }
        const tr = await fetch("/api/chat/threads", { credentials: "include" });
        if (cancelled) return;
        if (!tr.ok) {
          const id = uid();
          persistenceEnabledRef.current = false;
          setSessions([{ id, title: "New chat" }]);
          setActiveId(id);
          setMessagesBySession({ [id]: [] });
          messagesLoadedForThreadRef.current = new Set([id]);
          setHydrated(true);
          return;
        }
        const payload = (await tr.json()) as { threads?: { id: string; title: string }[] };
        let list = payload.threads ?? [];
        if (list.length === 0) {
          const cr = await fetch("/api/chat/threads", {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: "{}",
          });
          if (cancelled) return;
          if (!cr.ok) {
            const id = uid();
            persistenceEnabledRef.current = false;
            setSessions([{ id, title: "New chat" }]);
            setActiveId(id);
            setMessagesBySession({ [id]: [] });
            messagesLoadedForThreadRef.current = new Set([id]);
            setHydrated(true);
            return;
          }
          const row = (await cr.json()) as { id: string; title: string };
          list = [{ id: row.id, title: row.title }];
        }
        if (cancelled) return;
        persistenceEnabledRef.current = true;
        const sessList = list.map((t) => ({ id: t.id, title: t.title || "New chat" }));
        const msgMap: Record<string, ChatMessage[]> = Object.fromEntries(
          sessList.map((s) => [s.id, [] as ChatMessage[]]),
        );
        let focusId = sessList[0]!.id;
        for (const s of sessList) {
          serverChatSessionRef.current[s.id] = s.id;
        }
        setServerChatSessionByUi(Object.fromEntries(sessList.map((s) => [s.id, s.id])));
        const mr = await fetch(`/api/chat/threads/${focusId}/messages`, {
          credentials: "include",
        });
        if (cancelled) return;
        if (mr.ok) {
          const mp = (await mr.json()) as {
            messages?: { id: string; role: string; contentJson: unknown }[];
          };
          msgMap[focusId] = (mp.messages ?? [])
            .map(apiRowToChatMessage)
            .filter((m): m is ChatMessage => m != null);
        }
        const streaming = collectStreamingTurns(sessList, msgMap);
        if (streaming.length > 0) {
          const latest = streaming.reduce((a, b) =>
            a.after >= b.after ? a : b,
          );
          focusId = latest.threadId;
          if (focusId !== sessList[0]!.id && msgMap[focusId]?.length === 0) {
            const mr2 = await fetch(`/api/chat/threads/${focusId}/messages`, {
              credentials: "include",
            });
            if (!cancelled && mr2.ok) {
              const mp2 = (await mr2.json()) as {
                messages?: { id: string; role: string; contentJson: unknown }[];
              };
              msgMap[focusId] = (mp2.messages ?? [])
                .map(apiRowToChatMessage)
                .filter((m): m is ChatMessage => m != null);
            }
          }
        }
        messagesLoadedForThreadRef.current = new Set([focusId]);
        setSessions(sessList);
        setActiveId(focusId);
        setMessagesBySession(msgMap);
        setHydrated(true);
      } catch {
        if (cancelled) return;
        const id = uid();
        persistenceEnabledRef.current = false;
        setSessions([{ id, title: "New chat" }]);
        setActiveId(id);
        setMessagesBySession({ [id]: [] });
        messagesLoadedForThreadRef.current = new Set([id]);
        setHydrated(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(
    () => () => {
      for (const c of Object.values(abortBySessionRef.current)) {
        c.abort();
      }
      abortBySessionRef.current = {};
      streamingSidsRef.current.clear();
    },
    [],
  );

  const updateAssistantRun = useCallback(
    (sessionId: string, assistantMessageId: string, updater: (r: RunState) => RunState) => {
      setMessagesBySession((prev) => {
        const oldList = prev[sessionId];
        if (!oldList) return prev;
        const i = oldList.findIndex((m) => m.id === assistantMessageId);
        if (i === -1) return prev;
        const row = oldList[i]!;
        if (row.role !== "assistant") return prev;
        const nextRun = updater(row.run);
        if (nextRun === row.run) return prev;
        const list = oldList.slice();
        list[i] = { ...row, run: nextRun };
        const next = { ...prev, [sessionId]: list };
        messagesBySessionRef.current = next;
        return next;
      });
    },
    [],
  );

  const persistThreadToServer = useCallback(async (threadId: string) => {
    if (!persistenceEnabledRef.current) return;
    const msgs = messagesReadyToPersist(messagesBySessionRef.current[threadId] ?? []);
    if (msgs.length === 0) return;
    const title =
      sessionsRef.current.find((s) => s.id === threadId)?.title?.trim() || "New chat";
    try {
      await fetch(`/api/chat/threads/${threadId}/messages`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: msgs.map(chatMessageToApiRow),
          title,
        }),
      });
    } catch {
      /* ignore */
    }
  }, []);

  const schedulePersistThread = useCallback(
    (threadId: string, delayMs = 400) => {
      if (!persistenceEnabledRef.current) return;
      const prev = persistDebounceRef.current[threadId];
      if (prev) clearTimeout(prev);
      persistDebounceRef.current[threadId] = setTimeout(() => {
        delete persistDebounceRef.current[threadId];
        void persistThreadToServer(threadId);
      }, delayMs);
    },
    [persistThreadToServer],
  );

  const syncQueueUi = useCallback((sid: string) => {
    const q = queuesRef.current[sid] ?? [];
    if (sid === activeIdRef.current) {
      setQueuedMessages(q.map((j) => ({ id: j.id, text: jobPreviewText(j) })));
    }
  }, []);

  const removeQueuedMessage = useCallback(
    (messageId: string) => {
      const sid = activeIdRef.current;
      const arr = queuesRef.current[sid];
      if (!arr) return;
      queuesRef.current[sid] = arr.filter((j) => j.id !== messageId);
      syncQueueUi(sid);
    },
    [syncQueueUi],
  );

  const tryDrainGlobalQueue = useCallback(() => {
    while (streamingSidsRef.current.size < MAX_CONCURRENT_CHAT_STREAMS) {
      let pickedSid: string | null = null;
      for (const s of sessionsRef.current) {
        if (streamingSidsRef.current.has(s.id)) continue;
        const q = queuesRef.current[s.id];
        if (q?.length) {
          pickedSid = s.id;
          break;
        }
      }
      if (!pickedSid) break;
      const arr = queuesRef.current[pickedSid];
      const nextJob = arr?.shift();
      if (!nextJob) break;
      syncQueueUi(pickedSid);
      runOutboundJobRef.current(pickedSid, nextJob);
    }
  }, [syncQueueUi]);

  const runOutboundJob = useCallback(
    (sid: string, job: OutboundJob) => {
      if (streamingSidsRef.current.has(sid)) return;
      if (streamingSidsRef.current.size >= MAX_CONCURRENT_CHAT_STREAMS) return;

      const trimmed = job.text.trim();
      const imgs = job.images.filter((i) => i.data.length > 0);
      const priorMessages = messagesBySessionRef.current[sid] ?? [];
      const label =
        (job.dropdownModelLabel || "").trim() || (job.model || "").trim() || "";

      const userMsgId = uid();
      const turnId = uid();
      const assistantMsgId = turnId;
      const useDetached = shouldUseDetachedStreamingForPayload(
        trimmed.length,
        imgs.length,
        persistenceEnabledRef.current,
      );
      const userImages =
        imgs.length > 0
          ? imgs.map((i) => ({
              id: i.id,
              previewUrl: `data:${i.media_type};base64,${i.data}`,
            }))
          : undefined;

      markStreamStart(sid);

      setMessagesBySession((prev) => {
        const nextList: ChatMessage[] = [
          ...(prev[sid] ?? []),
          { id: userMsgId, role: "user", text: trimmed, images: userImages },
          {
            id: assistantMsgId,
            role: "assistant",
            run: {
              ...initialRunState(),
              turnId,
              runId: turnId,
              streamStatus: useDetached ? "streaming" : "",
              sseAfter: -1,
              dropdownModelLabel: label,
              streamStartedAt: Date.now(),
            },
          },
        ];
        const next = { ...prev, [sid]: nextList };
        messagesBySessionRef.current = next;
        return next;
      });

      const nextTitle = trimmed
        ? trimmed.length > 48
          ? `${trimmed.slice(0, 46)}…`
          : trimmed
        : imgs.length > 1
          ? "Images"
          : "Image";

      setSessions((prev) =>
        prev.map((s) =>
          s.id === sid && (s.title === "New chat" || !s.title)
            ? { ...s, title: nextTitle }
            : s,
        ),
      );

      const controller = new AbortController();
      abortBySessionRef.current[sid] = controller;

      const serverSid = (serverChatSessionRef.current[sid] ?? "").trim();

      let clientTz = "";
      let clientLocale = "";
      try {
        clientTz = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
      } catch {
        /* ignore */
      }
      try {
        clientLocale = typeof navigator !== "undefined" ? navigator.language : "";
      } catch {
        /* ignore */
      }

      const body: Record<string, unknown> = {
        msg: trimmed,
        model: job.model || "",
        provider: job.provider || "",
        client_tz: clientTz || null,
        client_locale: clientLocale || null,
        images: imgs.map((i) => ({ media_type: i.media_type, data: i.data })),
      };
      const clientHistory = chatMessagesToClientHistory(priorMessages);
      if (clientHistory.length > 0) body.client_history = clientHistory;
      if (serverSid) body.session_id = serverSid;
      if (useDetached) body.turn_id = turnId;

      void (async () => {
        let detachedRunId: string | null = useDetached ? turnId : null;
        let sawDone = false;
        try {
          if (persistenceEnabledRef.current) {
            setTimeout(() => {
              void persistThreadToServer(sid);
            }, 0);
          }

          const authHeaders: Record<string, string> = {};
          try {
            const supabase = createBrowserSupabaseClient();
            const { data } = await supabase.auth.getSession();
            if (data.session?.access_token) {
              authHeaders.Authorization = `Bearer ${data.session.access_token}`;
            }
          } catch {
            /* Supabase not configured in env — Composio falls back to backend default user */
          }

          let streamRes: Response;
          if (useDetached) {
            const startRes = await fetch("/koraku-api/runs", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
                ...authHeaders,
              },
              body: JSON.stringify(body),
              signal: controller.signal,
            });

            if (!startRes.ok) {
              const errText = await startRes.text().catch(() => startRes.statusText);
              updateAssistantRun(sid, assistantMsgId, (r) => ({
                ...r,
                error: r.error || `HTTP ${startRes.status}: ${errText.slice(0, 400)}`,
                statusText: "Request failed",
              }));
              return;
            }

            const startJson = (await startRes.json()) as { run_id?: string };
            const runId = (startJson.run_id ?? "").trim();
            if (!runId) {
              updateAssistantRun(sid, assistantMsgId, (r) => ({
                ...r,
                error: r.error || "Missing run_id from server",
                statusText: "Request failed",
              }));
              return;
            }

            detachedRunId = runId;
            if (runId !== turnId) {
              updateAssistantRun(sid, assistantMsgId, (r) => ({
                ...r,
                turnId,
                runId,
              }));
            }

            streamRes = await fetch(
              `/koraku-api/runs/${encodeURIComponent(runId)}/stream?after=-1`,
              {
                method: "GET",
                headers: {
                  Accept: "text/event-stream",
                  ...authHeaders,
                },
                signal: controller.signal,
              },
            );
          } else {
            streamRes = await fetch("/koraku-api/stream", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                Accept: "text/event-stream",
                ...authHeaders,
              },
              body: JSON.stringify(body),
              signal: controller.signal,
            });
          }

          if (!streamRes.ok) {
            let extra = "";
            if (detachedRunId && streamRes.status === 404) {
              const st = await fetchDetachedRunStatusJson(detachedRunId, authHeaders);
              if (st?.state === "not_found" && st.hint) {
                extra = ` ${st.hint}`;
              }
            }
            const errText = await streamRes.text().catch(() => streamRes.statusText);
            updateAssistantRun(sid, assistantMsgId, (r) => ({
              ...r,
              error:
                r.error ||
                `Stream HTTP ${streamRes.status}: ${errText.slice(0, 400)}${extra}`.trim(),
              statusText: "Subscribe failed",
            }));
            return;
          }

          const reader = streamRes.body?.getReader();
          if (!reader) {
            updateAssistantRun(sid, assistantMsgId, (r) => ({
              ...r,
              error: r.error || "No response body",
              statusText: "Stream error",
            }));
            return;
          }

          sawDone = await ingestKorakuSseFromReader(reader, {
            sessionId: sid,
            assistantMsgId,
            runId: detachedRunId,
            serverChatSessionRef,
            setServerChatSessionByUi,
            updateAssistantRun,
            onSseAfter: detachedRunId
              ? (after) => {
                  updateAssistantRun(sid, assistantMsgId, (r) =>
                    r.sseAfter === after ? r : { ...r, sseAfter: after },
                  );
                  schedulePersistThread(sid);
                }
              : undefined,
          });
        } catch (e) {
          if ((e as Error)?.name === "AbortError") return;
          updateAssistantRun(sid, assistantMsgId, (r) => ({
            ...r,
            error: r.error || String((e as Error)?.message || e),
            statusText: "Connection error",
          }));
        } finally {
          if (detachedRunId) {
            updateAssistantRun(sid, assistantMsgId, (r) => ({
              ...r,
              streamStatus: sawDone
                ? finalizeTurnStreamStatus(r.error, true)
                : r.streamStatus,
            }));
          }
          if (abortBySessionRef.current[sid] === controller) {
            delete abortBySessionRef.current[sid];
          }
          markStreamEnd(sid);
          const aborted = controller.signal.aborted;
          setTimeout(() => {
            void persistThreadToServer(sid);
            if (aborted) tryDrainGlobalQueueRef.current();
          }, 0);
          if (aborted) return;
          const arrSame = queuesRef.current[sid];
          const nextSame = arrSame?.length ? arrSame.shift()! : undefined;
          syncQueueUi(sid);
          if (nextSame) {
            runOutboundJobRef.current(sid, nextSame);
          } else {
            queueMicrotask(() => tryDrainGlobalQueueRef.current());
          }
        }
      })();
    },
    [
      markStreamEnd,
      markStreamStart,
      persistThreadToServer,
      schedulePersistThread,
      syncQueueUi,
      updateAssistantRun,
    ],
  );

  runOutboundJobRef.current = runOutboundJob;
  tryDrainGlobalQueueRef.current = tryDrainGlobalQueue;

  const resumeStreamingTurns = useCallback(() => {
    if (!hydrated || typeof window === "undefined") return;
    if (!persistenceEnabledRef.current) return;

    const sessionIds = new Set(sessionsRef.current.map((s) => s.id));
    const pending = collectStreamingTurns(
      sessionsRef.current,
      messagesBySessionRef.current,
    );

    for (const p of pending) {
      if (!sessionIds.has(p.threadId)) continue;
      if (detachResumeStartedRef.current.has(p.turnId)) continue;
      if (streamingSidsRef.current.has(p.threadId)) continue;

      detachResumeStartedRef.current.add(p.turnId);
      if (activeIdRef.current !== p.threadId) {
        setActiveId(p.threadId);
      }

      void (async () => {
        let streamMarked = false;
        let controller: AbortController | null = null;
        let sawDone = false;
        try {
          if (!messagesBySessionRef.current[p.threadId]?.some((m) => m.id === p.assistantMsgId)) {
            try {
              const mr = await fetch(`/api/chat/threads/${p.threadId}/messages`, {
                credentials: "include",
              });
              if (!mr.ok) {
                updateAssistantRun(p.threadId, p.assistantMsgId, (r) => ({
                  ...r,
                  streamStatus: "failed",
                  error: r.error || "Could not load thread for resume",
                }));
                return;
              }
              const mp = (await mr.json()) as {
                messages?: { id: string; role: string; contentJson: unknown }[];
              };
              const list = (mp.messages ?? [])
                .map(apiRowToChatMessage)
                .filter((m): m is ChatMessage => m != null);
              setMessagesBySession((prev) => ({ ...prev, [p.threadId]: list }));
              messagesLoadedForThreadRef.current.add(p.threadId);
            } catch {
              return;
            }
          }

          markStreamStart(p.threadId);
          streamMarked = true;
          controller = new AbortController();
          abortBySessionRef.current[p.threadId] = controller;

          const authHeaders: Record<string, string> = {};
          try {
            const supabase = createBrowserSupabaseClient();
            const { data } = await supabase.auth.getSession();
            if (data.session?.access_token) {
              authHeaders.Authorization = `Bearer ${data.session.access_token}`;
            }
          } catch {
            /* ignore */
          }

          updateAssistantRun(p.threadId, p.assistantMsgId, (r) => ({
            ...r,
            statusText: "Reconnecting…",
            error: null,
            streamStatus: "streaming",
          }));

          const streamRes = await fetch(
            `/koraku-api/runs/${encodeURIComponent(p.turnId)}/stream?after=${encodeURIComponent(String(p.after))}`,
            {
              method: "GET",
              headers: { Accept: "text/event-stream", ...authHeaders },
              signal: controller.signal,
            },
          );

          if (!streamRes.ok) {
            let extra = "";
            if (streamRes.status === 404) {
              const st = await fetchDetachedRunStatusJson(p.turnId, authHeaders);
              if (st?.state === "not_found" && st.hint) {
                extra = ` ${st.hint}`;
              }
            }
            updateAssistantRun(p.threadId, p.assistantMsgId, (r) => ({
              ...r,
              streamStatus: "failed",
              error:
                r.error ||
                `Reconnect HTTP ${streamRes.status}${extra}`.trim(),
              statusText: "Subscribe failed",
            }));
            return;
          }

          const reader = streamRes.body?.getReader();
          if (!reader) {
            updateAssistantRun(p.threadId, p.assistantMsgId, (r) => ({
              ...r,
              streamStatus: "failed",
              error: r.error || "No response body",
              statusText: "Stream error",
            }));
            return;
          }

          sawDone = await ingestKorakuSseFromReader(reader, {
            sessionId: p.threadId,
            assistantMsgId: p.assistantMsgId,
            runId: p.turnId,
            serverChatSessionRef,
            setServerChatSessionByUi,
            updateAssistantRun,
            onSseAfter: (after) => {
              updateAssistantRun(p.threadId, p.assistantMsgId, (r) =>
                r.sseAfter === after ? r : { ...r, sseAfter: after },
              );
              schedulePersistThread(p.threadId);
            },
          });
        } catch (e) {
          if ((e as Error)?.name !== "AbortError") {
            updateAssistantRun(p.threadId, p.assistantMsgId, (r) => ({
              ...r,
              streamStatus: "failed",
              error: r.error || String((e as Error)?.message || e),
              statusText: "Reconnect error",
            }));
          }
        } finally {
          updateAssistantRun(p.threadId, p.assistantMsgId, (r) => ({
            ...r,
            streamStatus: sawDone
              ? finalizeTurnStreamStatus(r.error, true)
              : r.streamStatus,
          }));
          detachResumeStartedRef.current.delete(p.turnId);
          if (streamMarked) {
            if (controller && abortBySessionRef.current[p.threadId] === controller) {
              delete abortBySessionRef.current[p.threadId];
            }
            markStreamEnd(p.threadId);
            setTimeout(() => {
              void persistThreadToServer(p.threadId);
              tryDrainGlobalQueueRef.current();
            }, 0);
          }
        }
      })();
    }
  }, [
    hydrated,
    markStreamEnd,
    markStreamStart,
    persistThreadToServer,
    schedulePersistThread,
    updateAssistantRun,
  ]);

  resumeStreamingTurnsRef.current = resumeStreamingTurns;

  useEffect(() => {
    resumeStreamingTurns();
    return () => {
      detachResumeStartedRef.current.clear();
    };
  }, [hydrated, sessions, resumeStreamingTurns]);

  const send = useCallback(
    (
      text: string,
      provider: string,
      model: string,
      dropdownModelLabel: string,
      images: ComposerImage[] = [],
    ) => {
      const trimmed = text.trim();
      const imgs = images.filter((i) => i.data.length > 0);
      if (!trimmed && imgs.length === 0) return;
      if (!hydrated) return;

      const sid = activeIdRef.current;
      const job: OutboundJob = {
        id: uid(),
        text: trimmed,
        provider,
        model,
        dropdownModelLabel,
        images: imgs.map((i) => ({ ...i })),
      };

      if (streamingSidsRef.current.has(sid)) {
        queuesRef.current[sid] ??= [];
        queuesRef.current[sid].push(job);
        syncQueueUi(sid);
        return;
      }

      if (streamingSidsRef.current.size >= MAX_CONCURRENT_CHAT_STREAMS) {
        queuesRef.current[sid] ??= [];
        queuesRef.current[sid].push(job);
        syncQueueUi(sid);
        return;
      }

      runOutboundJob(sid, job);
    },
    [hydrated, runOutboundJob, syncQueueUi],
  );

  const newChat = useCallback(async () => {
    const sid = activeIdRef.current;
    if (sid) {
      const msgs = messagesBySessionRef.current[sid] ?? [];
      const sessionRow = sessionsRef.current.find((x) => x.id === sid);
      const title = sessionRow?.title?.trim() ?? "";
      const defaultTitle = !title || title === "New chat";
      if (
        msgs.length === 0 &&
        defaultTitle &&
        !streamingSidsRef.current.has(sid)
      ) {
        return;
      }
    }

    if (newChatInFlightRef.current) return;
    newChatInFlightRef.current = true;
    try {
      if (persistenceEnabledRef.current) {
        try {
          const res = await fetch("/api/chat/threads", {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: "{}",
          });
          if (res.ok) {
            const row = (await res.json()) as { id: string; title: string };
            const id = row.id;
            serverChatSessionRef.current[id] = id;
            setServerChatSessionByUi((prev) => ({ ...prev, [id]: id }));
            setSessions((s) => [{ id, title: row.title || "New chat" }, ...s]);
            setMessagesBySession((m) => ({ ...m, [id]: [] }));
            setActiveId(id);
            setQueuedMessages([]);
            messagesLoadedForThreadRef.current.add(id);
            return;
          }
        } catch {
          /* fall through to local-only chat */
        }
      }
      const id = uid();
      setSessions((s) => [{ id, title: "New chat" }, ...s]);
      setMessagesBySession((m) => ({ ...m, [id]: [] }));
      setActiveId(id);
      setQueuedMessages([]);
      messagesLoadedForThreadRef.current.add(id);
    } finally {
      newChatInFlightRef.current = false;
    }
  }, []);

  const selectSession = useCallback((id: string) => {
    setActiveId(id);
    const q = queuesRef.current[id] ?? [];
    setQueuedMessages(q.map((j) => ({ id: j.id, text: jobPreviewText(j) })));

    if (!persistenceEnabledRef.current) return;
    if (messagesLoadedForThreadRef.current.has(id)) {
      setTimeout(() => resumeStreamingTurnsRef.current(), 0);
      return;
    }
    if (messagesLoadInflightRef.current.has(id)) return;
    messagesLoadInflightRef.current.add(id);
    setMessagesLoadingSessionIds((prev) => (prev.includes(id) ? prev : [...prev, id]));

    void (async () => {
      try {
        const res = await fetch(`/api/chat/threads/${id}/messages`, {
          credentials: "include",
        });
        if (!res.ok) {
          return;
        }
        const body = (await res.json()) as {
          messages?: { id: string; role: string; contentJson: unknown }[];
        };
        const list = (body.messages ?? [])
          .map(apiRowToChatMessage)
          .filter((m): m is ChatMessage => m != null);
        setMessagesBySession((prev) => {
          const next = { ...prev, [id]: list };
          messagesBySessionRef.current = next;
          return next;
        });
        messagesLoadedForThreadRef.current.add(id);
        setTimeout(() => resumeStreamingTurnsRef.current(), 0);
      } catch {
        /* not marked loaded */
      } finally {
        messagesLoadInflightRef.current.delete(id);
        setMessagesLoadingSessionIds((prev) => prev.filter((x) => x !== id));
      }
    })();
  }, []);

  const deleteSession = useCallback(
    async (id: string) => {
      if (!sessionsRef.current.some((s) => s.id === id)) return;

      setDeletingSessionIds((prev) =>
        prev.includes(id) ? prev : [...prev, id],
      );
      try {
        const controller = abortBySessionRef.current[id];
        if (controller) {
          controller.abort();
          delete abortBySessionRef.current[id];
        }
        markStreamEnd(id);
        delete queuesRef.current[id];
        delete serverChatSessionRef.current[id];
        messagesLoadedForThreadRef.current.delete(id);

        if (persistenceEnabledRef.current) {
          try {
            await fetch(`/api/chat/threads/${id}`, {
              method: "DELETE",
              credentials: "include",
            });
          } catch {
            /* still remove locally */
          }
        }

        const wasActive = activeIdRef.current === id;
        const nextSessions = sessionsRef.current.filter((s) => s.id !== id);

        if (nextSessions.length === 0) {
          if (persistenceEnabledRef.current) {
            try {
              const res = await fetch("/api/chat/threads", {
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
                body: "{}",
              });
              if (res.ok) {
                const row = (await res.json()) as { id: string; title: string };
                const nid = row.id;
                serverChatSessionRef.current = { [nid]: nid };
                setServerChatSessionByUi({ [nid]: nid });
                setSessions([{ id: nid, title: row.title || "New chat" }]);
                setMessagesBySession({ [nid]: [] });
                setActiveId(nid);
                setQueuedMessages([]);
                messagesLoadedForThreadRef.current = new Set([nid]);
                queueMicrotask(() => tryDrainGlobalQueueRef.current());
                return;
              }
            } catch {
              /* fall through to local-only replacement */
            }
          }
          const nid = uid();
          serverChatSessionRef.current = {};
          setServerChatSessionByUi({});
          setSessions([{ id: nid, title: "New chat" }]);
          setMessagesBySession({ [nid]: [] });
          setActiveId(nid);
          setQueuedMessages([]);
          messagesLoadedForThreadRef.current = new Set([nid]);
          queueMicrotask(() => tryDrainGlobalQueueRef.current());
          return;
        }

        setSessions(nextSessions);
        setMessagesBySession((m) => {
          const n = { ...m };
          delete n[id];
          return n;
        });
        setServerChatSessionByUi((prev) => {
          if (!prev[id]) return prev;
          const n = { ...prev };
          delete n[id];
          return n;
        });

        if (wasActive) {
          const fallbackId = nextSessions[0]!.id;
          setActiveId(fallbackId);
          const q = queuesRef.current[fallbackId] ?? [];
          setQueuedMessages(q.map((j) => ({ id: j.id, text: jobPreviewText(j) })));
        }
        queueMicrotask(() => tryDrainGlobalQueueRef.current());
      } finally {
        setDeletingSessionIds((prev) => prev.filter((x) => x !== id));
      }
    },
    [markStreamEnd],
  );

  const shell = useMemo(
    (): KorakuChatShellApi => ({
      hydrated,
      sessions,
      activeId,
      streamingSessionIds,
      deletingSessionIds,
      selectSession,
      newChat,
      deleteSession,
    }),
    [
      hydrated,
      sessions,
      activeId,
      streamingSessionIds,
      deletingSessionIds,
      selectSession,
      newChat,
      deleteSession,
    ],
  );

  const thread = useMemo(
    (): KorakuChatThreadApi => ({
      hydrated,
      messagesLoadingSessionIds,
      activeId,
      messages,
      busy,
      queuedMessages,
      removeQueuedMessage,
      send,
      serverChatSessionByUi,
    }),
    [
      hydrated,
      messagesLoadingSessionIds,
      activeId,
      messages,
      busy,
      queuedMessages,
      removeQueuedMessage,
      send,
      serverChatSessionByUi,
    ],
  );

  return useMemo(
    () => ({ shell, thread }),
    [shell, thread],
  );
}

export type KorakuChatShellApi = {
  hydrated: boolean;
  sessions: ChatSession[];
  activeId: string;
  streamingSessionIds: string[];
  deletingSessionIds: string[];
  selectSession: (id: string) => void;
  newChat: () => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
};

export type KorakuChatThreadApi = {
  hydrated: boolean;
  messagesLoadingSessionIds: string[];
  activeId: string;
  messages: ChatMessage[];
  busy: boolean;
  queuedMessages: QueuedMessagePreview[];
  removeQueuedMessage: (messageId: string) => void;
  send: (
    text: string,
    provider: string,
    model: string,
    dropdownModelLabel: string,
    images?: ComposerImage[],
  ) => void;
  serverChatSessionByUi: Record<string, string>;
};

export type KorakuChatStore = ReturnType<typeof useKorakuChat>;
