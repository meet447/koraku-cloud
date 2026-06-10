"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { initialRunState, type RunState } from "@/lib/korakuReducer";
import type { QueuedMessagePreview } from "@/components/MessageQueueBar";
import {
  detachedChatMode,
  fetchDetachedRunStatusJson,
  refreshDetachedRunsCapability,
  shouldUseDetachedStreamingForPayload,
} from "@/lib/koraku-chat/detached-streaming";
import {
  apiRowToChatMessage,
  chatMessageToApiRow,
  chatMessagesToClientHistory,
  messagesReadyToPersist,
} from "@/lib/koraku-chat/persistence";
import {
  collectStreamingTurns,
  finalizeTurnStreamStatus,
  ingestKorakuSseFromReader,
  runStateForStreamReplay,
} from "@/lib/koraku-chat/sse-ingest";
import {
  isDefaultChatTitle,
  isEmptyUnusedSession,
  jobPreviewText,
  uid,
} from "@/lib/koraku-chat/session-utils";
import {
  EMPTY_THREAD_MESSAGES,
  MAX_CONCURRENT_CHAT_STREAMS,
  type ChatMessage,
  type ChatSession,
  type OutboundJob,
} from "@/lib/koraku-chat/types";
import { safeError } from "@/lib/safe-log";
import { supabaseAuthHeaders } from "@/lib/supabase/fetch-auth";
import { sortChatSessions } from "@/lib/chat-sessions";
import { rememberLastActiveThreadId, readLastActiveThreadId } from "@/lib/last-active-thread";
import type { ComposerAttachment } from "@/lib/composer-attachments";
import type { ComposerImage } from "@/lib/composer-images";
import { createBrowserSupabaseClient } from "@/lib/supabase/browser";

export type { ChatMessage, ChatSession, OutboundJob } from "@/lib/koraku-chat/types";
export { MAX_CONCURRENT_CHAT_STREAMS } from "@/lib/koraku-chat/types";

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
  /** Session ids running ``refreshSession`` (iMessage history reload). */
  const [refreshingSessionIds, setRefreshingSessionIds] = useState<string[]>([]);
  /** Bumped to reload workspace tree for the active session (e.g. after iMessage sync). */
  const [workspaceRefreshToken, setWorkspaceRefreshToken] = useState(0);
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
  /** UI-only chats until the user sends the first message (no ``chat_thread`` row yet). */
  const draftSessionIdsRef = useRef<Set<string>>(new Set());
  /** In-flight ``POST /api/chat/threads`` for draft sessions (deduped per id). */
  const threadCreatePromisesRef = useRef<Map<string, Promise<boolean>>>(new Map());
  /** Dedupe detached-run resume side-effects (Strict Mode / re-renders). */
  const detachResumeStartedRef = useRef<Set<string>>(new Set());
  const persistDebounceRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const resumeStreamingTurnsRef = useRef<() => void>(() => {});
  const fetchThreadMessagesRef = useRef<(id: string, options?: { force?: boolean }) => Promise<boolean>>(
    async () => false,
  );

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
        const threadsPromise = fetch("/api/chat/threads", { credentials: "include" });
        const userPromise = supabase.auth.getUser();
        const [{ data: { user } }, tr] = await Promise.all([
          userPromise,
          threadsPromise,
        ]);
        if (cancelled) return;
        if (!user) {
          const id = uid();
          persistenceEnabledRef.current = false;
          setSessions([{ id, title: "New chat" }]);
          setActiveId(id);
          setMessagesBySession({ [id]: [] });
          messagesLoadedForThreadRef.current = new Set([id]);
          setHydrated(true);
          return;
        }
        if (!tr.ok) {
          safeError("[useKorakuChat] thread list failed", tr.status);
          const id = uid();
          // Keep persistence on for signed-in users so messages still save if the list
          // endpoint fails transiently (e.g. pending DB migration).
          persistenceEnabledRef.current = true;
          draftSessionIdsRef.current.add(id);
          setSessions([{ id, title: "New chat" }]);
          setActiveId(id);
          setMessagesBySession({ [id]: [] });
          messagesLoadedForThreadRef.current = new Set([id]);
          setHydrated(true);
          return;
        }
        const payload = (await tr.json()) as {
          threads?: {
            id: string;
            title: string;
            channel?: string;
            pinned?: boolean;
          }[];
        };
        let list = payload.threads ?? [];
        if (list.length === 0) {
          const id = uid();
          draftSessionIdsRef.current.add(id);
          persistenceEnabledRef.current = true;
          setSessions([{ id, title: "New chat" }]);
          setActiveId(id);
          setMessagesBySession({ [id]: [] });
          messagesLoadedForThreadRef.current = new Set([id]);
          setHydrated(true);
          return;
        }
        if (cancelled) return;
        persistenceEnabledRef.current = true;
        const sessList = list.map((t) => ({
          id: t.id,
          title: t.title || "New chat",
          channel: t.channel,
          pinned: t.pinned,
        }));
        const newId = uid();
        draftSessionIdsRef.current.add(newId);
        const lastActive = readLastActiveThreadId();
        const activeThreadId =
          lastActive && sessList.some((s) => s.id === lastActive) ? lastActive : newId;
        const sessionsWithNew = sortChatSessions([
          { id: newId, title: "New chat" },
          ...sessList,
        ]);
        const msgMap: Record<string, ChatMessage[]> = Object.fromEntries(
          sessionsWithNew.map((s) => [s.id, [] as ChatMessage[]]),
        );
        for (const s of sessList) {
          serverChatSessionRef.current[s.id] = s.id;
        }
        setServerChatSessionByUi(Object.fromEntries(sessList.map((s) => [s.id, s.id])));

        messagesLoadedForThreadRef.current.add(newId);
        setSessions(sessionsWithNew);
        setActiveId(activeThreadId);
        setMessagesBySession(msgMap);
        setHydrated(true);
        if (activeThreadId !== newId) {
          queueMicrotask(() => {
            void fetchThreadMessagesRef.current(activeThreadId);
          });
        }
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

  useEffect(() => {
    if (!hydrated || !persistenceEnabledRef.current) return;
    void refreshDetachedRunsCapability();
  }, [hydrated]);

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

  const ensureDraftThreadSaved = useCallback(
    async (threadId: string, title: string): Promise<boolean> => {
      if (!persistenceEnabledRef.current) return false;
      if (!draftSessionIdsRef.current.has(threadId)) return true;

      const existing = threadCreatePromisesRef.current.get(threadId);
      if (existing) return existing;

      const promise = (async () => {
        try {
          const res = await fetch("/api/chat/threads", {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: threadId, title }),
          });
          if (!res.ok) return false;
          draftSessionIdsRef.current.delete(threadId);
          serverChatSessionRef.current[threadId] = threadId;
          rememberLastActiveThreadId(threadId);
          setServerChatSessionByUi((prev) =>
            prev[threadId] === threadId ? prev : { ...prev, [threadId]: threadId },
          );
          return true;
        } catch {
          return false;
        } finally {
          threadCreatePromisesRef.current.delete(threadId);
        }
      })();

      threadCreatePromisesRef.current.set(threadId, promise);
      return promise;
    },
    [],
  );

  const persistThreadToServer = useCallback(
    async (threadId: string) => {
      if (!persistenceEnabledRef.current) return;
      const title =
        sessionsRef.current.find((s) => s.id === threadId)?.title?.trim() || "New chat";
      if (!(await ensureDraftThreadSaved(threadId, title))) return;
      const msgs = messagesReadyToPersist(messagesBySessionRef.current[threadId] ?? []);
      if (msgs.length === 0) return;
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
    },
    [ensureDraftThreadSaved],
  );

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

  const discardEmptySession = useCallback(async (sid: string) => {
    if (
      !isEmptyUnusedSession(
        sid,
        sessionsRef.current,
        messagesBySessionRef.current,
        streamingSidsRef.current,
      )
    ) {
      return;
    }

    const isDraft = draftSessionIdsRef.current.has(sid);
    if (isDraft) {
      draftSessionIdsRef.current.delete(sid);
    } else if (persistenceEnabledRef.current) {
      try {
        await fetch(`/api/chat/threads/${encodeURIComponent(sid)}`, {
          method: "DELETE",
          credentials: "include",
        });
      } catch {
        /* still remove locally */
      }
      delete serverChatSessionRef.current[sid];
      setServerChatSessionByUi((prev) => {
        if (!prev[sid]) return prev;
        const next = { ...prev };
        delete next[sid];
        return next;
      });
    }

    messagesLoadedForThreadRef.current.delete(sid);
    delete queuesRef.current[sid];
    setSessions((s) => {
      const next = sortChatSessions(s.filter((x) => x.id !== sid));
      if (activeIdRef.current === sid && next.length > 0) {
        const fallbackId = next[0]!.id;
        setActiveId(fallbackId);
        const q = queuesRef.current[fallbackId] ?? [];
        setQueuedMessages(q.map((j) => ({ id: j.id, text: jobPreviewText(j) })));
      }
      return next;
    });
    setMessagesBySession((m) => {
      if (!m[sid]) return m;
      const next = { ...m };
      delete next[sid];
      return next;
    });
  }, []);

  const discardEmptyActiveSession = useCallback(async () => {
    const sid = activeIdRef.current;
    if (!sid) return;
    await discardEmptySession(sid);
  }, [discardEmptySession]);

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
      void (async () => {
        if (streamingSidsRef.current.has(sid)) return;
        if (streamingSidsRef.current.size >= MAX_CONCURRENT_CHAT_STREAMS) return;

        const trimmed = job.text.trim();
        const imgs = job.images.filter((i) => i.data.length > 0);
        const atts = job.attachments.filter((a) => a.data.length > 0);
        const priorMessages = messagesBySessionRef.current[sid] ?? [];
        const label =
          (job.dropdownModelLabel || "").trim() || (job.model || "").trim() || "";

        const userMsgId = uid();
        const turnId = uid();
        const assistantMsgId = turnId;
        if (persistenceEnabledRef.current && detachedChatMode() === "default") {
          void refreshDetachedRunsCapability();
        }
        const useDetached = shouldUseDetachedStreamingForPayload(
          trimmed.length,
          imgs.length,
          persistenceEnabledRef.current,
          atts.length,
        );
        const userImages =
          imgs.length > 0
            ? imgs.map((i) => ({
                id: i.id,
                previewUrl: `data:${i.media_type};base64,${i.data}`,
              }))
            : undefined;

        const nextTitle = trimmed
          ? trimmed.length > 48
            ? `${trimmed.slice(0, 46)}…`
            : trimmed
          : imgs.length > 1
            ? "Images"
            : imgs.length === 1
              ? "Image"
              : atts.length > 1
                ? "Attachments"
                : atts[0]?.filename || "Attachment";

        markStreamStart(sid);

        setMessagesBySession((prev) => {
          const nextList: ChatMessage[] = [
            ...(prev[sid] ?? []),
            {
              id: userMsgId,
              role: "user",
              text: trimmed,
              images: userImages,
              attachments:
                atts.length > 0
                  ? atts.map((a) => ({ id: a.id, filename: a.filename }))
                  : undefined,
            },
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

        setSessions((prev) =>
          prev.map((s) =>
            s.id === sid && isDefaultChatTitle(s.title)
              ? { ...s, title: nextTitle }
              : s,
          ),
        );

        if (persistenceEnabledRef.current) {
          serverChatSessionRef.current[sid] = sid;
          setServerChatSessionByUi((prev) =>
            prev[sid] === sid ? prev : { ...prev, [sid]: sid },
          );
          if (draftSessionIdsRef.current.has(sid)) {
            void ensureDraftThreadSaved(sid, nextTitle);
          } else {
            rememberLastActiveThreadId(sid);
          }
        }

        const controller = new AbortController();
        abortBySessionRef.current[sid] = controller;
        const authHeadersPromise = supabaseAuthHeaders();

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
          attachments: atts.map((a) => ({
            filename: a.filename,
            media_type: a.media_type,
            data: a.data,
          })),
        };
        const clientHistory = chatMessagesToClientHistory(priorMessages);
        if (clientHistory.length > 0) body.client_history = clientHistory;
        if (persistenceEnabledRef.current) {
          body.session_id = sid;
        } else {
          const serverSid = (serverChatSessionRef.current[sid] ?? "").trim();
          if (serverSid) body.session_id = serverSid;
        }
        if (useDetached) body.turn_id = turnId;

        let detachedRunId: string | null = useDetached ? turnId : null;
        let sawDone = false;
        try {
          if (persistenceEnabledRef.current) {
            setTimeout(() => {
              void persistThreadToServer(sid);
            }, 0);
          }

          const authHeaders = await authHeadersPromise;

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
              let displayError = `HTTP ${startRes.status}: ${errText.slice(0, 400)}`;
              if (startRes.status === 402) {
                try {
                  const body = JSON.parse(errText) as { detail?: { message?: string } };
                  displayError =
                    body.detail?.message ||
                    "Monthly credit limit reached. Open Settings → Usage for details.";
                } catch {
                  displayError =
                    "Monthly credit limit reached. Open Settings → Usage for details.";
                }
              }
              updateAssistantRun(sid, assistantMsgId, (r) => ({
                ...r,
                error: r.error || displayError,
                statusText:
                  startRes.status === 402 ? "Credits exhausted" : "Request failed",
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
            let displayError = `Stream HTTP ${streamRes.status}: ${errText.slice(0, 400)}${extra}`.trim();
            if (streamRes.status === 402) {
              try {
                const body = JSON.parse(errText) as {
                  detail?: { message?: string };
                };
                displayError =
                  body.detail?.message ||
                  "Monthly credit limit reached. Open Settings → Usage for details.";
              } catch {
                displayError =
                  "Monthly credit limit reached. Open Settings → Usage for details.";
              }
            }
            updateAssistantRun(sid, assistantMsgId, (r) => ({
              ...r,
              error: r.error || displayError,
              statusText: streamRes.status === 402 ? "Credits exhausted" : "Subscribe failed",
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
            if (persistenceEnabledRef.current) {
              void persistThreadToServer(sid);
            }
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
      ensureDraftThreadSaved,
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

          const authHeaders = await supabaseAuthHeaders();

          updateAssistantRun(p.threadId, p.assistantMsgId, (r) => runStateForStreamReplay(r));

          const streamRes = await fetch(
            `/koraku-api/runs/${encodeURIComponent(p.turnId)}/stream?after=-1`,
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
    if (!hydrated) return;
    resumeStreamingTurns();
    const started = detachResumeStartedRef.current;
    return () => {
      started.clear();
    };
  }, [hydrated, resumeStreamingTurns]);

  const send = useCallback(
    (
      text: string,
      provider: string,
      model: string,
      dropdownModelLabel: string,
      images: ComposerImage[] = [],
      attachments: ComposerAttachment[] = [],
    ) => {
      const trimmed = text.trim();
      const imgs = images.filter((i) => i.data.length > 0);
      const atts = attachments.filter((a) => a.data.length > 0);
      if (!trimmed && imgs.length === 0 && atts.length === 0) return;
      if (!hydrated) return;

      const sid = activeIdRef.current;
      const job: OutboundJob = {
        id: uid(),
        text: trimmed,
        provider,
        model,
        dropdownModelLabel,
        images: imgs.map((i) => ({ ...i })),
        attachments: atts.map((a) => ({ ...a })),
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
    if (
      sid &&
      isEmptyUnusedSession(
        sid,
        sessionsRef.current,
        messagesBySessionRef.current,
        streamingSidsRef.current,
      )
    ) {
      return;
    }

    if (newChatInFlightRef.current) return;
    newChatInFlightRef.current = true;
    try {
      const id = uid();
      if (persistenceEnabledRef.current) {
        draftSessionIdsRef.current.add(id);
      }
      setSessions((s) => sortChatSessions([{ id, title: "New chat" }, ...s]));
      setMessagesBySession((m) => ({ ...m, [id]: [] }));
      setActiveId(id);
      setQueuedMessages([]);
      messagesLoadedForThreadRef.current.add(id);
    } finally {
      newChatInFlightRef.current = false;
    }
  }, []);

  const fetchThreadMessages = useCallback(
    async (id: string, options?: { force?: boolean }): Promise<boolean> => {
      if (!persistenceEnabledRef.current) return false;
      if (!options?.force && messagesLoadedForThreadRef.current.has(id)) {
        return true;
      }
      if (messagesLoadInflightRef.current.has(id)) return false;
      messagesLoadInflightRef.current.add(id);
      setMessagesLoadingSessionIds((prev) => (prev.includes(id) ? prev : [...prev, id]));
      try {
        const res = await fetch(`/api/chat/threads/${id}/messages`, {
          credentials: "include",
        });
        if (!res.ok) {
          return false;
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
        if (activeIdRef.current === id) {
          setTimeout(() => resumeStreamingTurnsRef.current(), 0);
        }
        return true;
      } catch {
        return false;
      } finally {
        messagesLoadInflightRef.current.delete(id);
        setMessagesLoadingSessionIds((prev) => prev.filter((x) => x !== id));
      }
    },
    [],
  );

  fetchThreadMessagesRef.current = fetchThreadMessages;

  const selectSession = useCallback(
    (id: string) => {
      const prev = activeIdRef.current;
      if (prev && prev !== id) {
        void discardEmptySession(prev);
      }
      setActiveId(id);
      if (!draftSessionIdsRef.current.has(id)) {
        rememberLastActiveThreadId(id);
      }
      const q = queuesRef.current[id] ?? [];
      setQueuedMessages(q.map((j) => ({ id: j.id, text: jobPreviewText(j) })));

      if (!persistenceEnabledRef.current) return;
      if (messagesLoadedForThreadRef.current.has(id)) {
        setTimeout(() => resumeStreamingTurnsRef.current(), 0);
        return;
      }
      void fetchThreadMessages(id);
    },
    [discardEmptySession, fetchThreadMessages],
  );

  const deleteSession = useCallback(
    async (id: string) => {
      const target = sessionsRef.current.find((s) => s.id === id);
      if (!target) return;
      if (target.channel === "imessage" || target.pinned) return;

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
        const wasDraft = draftSessionIdsRef.current.has(id);
        draftSessionIdsRef.current.delete(id);
        messagesLoadedForThreadRef.current.delete(id);

        if (persistenceEnabledRef.current && !wasDraft) {
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
          const nid = uid();
          if (persistenceEnabledRef.current) {
            draftSessionIdsRef.current.add(nid);
          }
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

        setSessions(sortChatSessions(nextSessions));
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

  const reloadSessions = useCallback(async () => {
    if (!persistenceEnabledRef.current) return;
    try {
      const tr = await fetch("/api/chat/threads", { credentials: "include" });
      if (!tr.ok) return;
      const payload = (await tr.json()) as {
        threads?: {
          id: string;
          title: string;
          channel?: string;
          pinned?: boolean;
        }[];
      };
      const list = (payload.threads ?? []).map((t) => ({
        id: t.id,
        title: t.title || "New chat",
        channel: t.channel,
        pinned: t.pinned,
      }));
      if (list.length === 0) return;
      setSessions(sortChatSessions(list));
      for (const s of list) {
        serverChatSessionRef.current[s.id] = s.id;
      }
      setServerChatSessionByUi(Object.fromEntries(list.map((s) => [s.id, s.id])));
    } catch {
      /* ignore */
    }
  }, []);

  const refreshSession = useCallback(
    async (id: string) => {
      const target = sessionsRef.current.find((s) => s.id === id);
      if (!target) return;
      if (target.channel !== "imessage" && !target.pinned) return;

      setRefreshingSessionIds((prev) => (prev.includes(id) ? prev : [...prev, id]));
      try {
        await reloadSessions();
        messagesLoadedForThreadRef.current.delete(id);
        await fetchThreadMessages(id, { force: true });
        if (activeIdRef.current === id) {
          setWorkspaceRefreshToken((t) => t + 1);
        }
      } finally {
        setRefreshingSessionIds((prev) => prev.filter((x) => x !== id));
      }
    },
    [fetchThreadMessages, reloadSessions],
  );

  const shell = useMemo(
    (): KorakuChatShellApi => ({
      hydrated,
      sessions,
      activeId,
      streamingSessionIds,
      deletingSessionIds,
      refreshingSessionIds,
      selectSession,
      newChat,
      deleteSession,
      refreshSession,
      discardEmptyActiveSession,
      reloadSessions,
    }),
    [
      hydrated,
      sessions,
      activeId,
      streamingSessionIds,
      deletingSessionIds,
      refreshingSessionIds,
      selectSession,
      newChat,
      deleteSession,
      refreshSession,
      discardEmptyActiveSession,
      reloadSessions,
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
      workspaceRefreshToken,
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
      workspaceRefreshToken,
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
  refreshingSessionIds: string[];
  selectSession: (id: string) => void;
  newChat: () => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
  refreshSession: (id: string) => Promise<void>;
  discardEmptyActiveSession: () => Promise<void>;
  reloadSessions: () => Promise<void>;
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
    attachments?: ComposerAttachment[],
  ) => void;
  serverChatSessionByUi: Record<string, string>;
  workspaceRefreshToken: number;
};

export type KorakuChatStore = ReturnType<typeof useKorakuChat>;
