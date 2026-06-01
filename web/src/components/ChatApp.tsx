"use client";

import { useVirtualizer } from "@tanstack/react-virtual";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import { PanelRight } from "lucide-react";
import { useKorakuChatThread } from "@/context/KorakuChatContext";
import type { ChatMessage } from "@/hooks/useKorakuChat";
import { Composer } from "./Composer";
import { MessageQueueBar } from "./MessageQueueBar";
import { ToolTimeline } from "./ToolTimeline";
import { MarkdownBody } from "./MarkdownBody";
import { AgentBusyRow } from "./AgentBusyRow";
import { BrandMark } from "./BrandMark";
import { WorkspacePanel } from "./WorkspacePanel";
import { RunWorkspaceAttachments } from "./RunWorkspaceAttachments";

/** Use windowed rendering when a thread has at least this many rows. */
const VIRTUALIZE_MESSAGE_COUNT = 10;

function ChatMessagesSkeleton() {
  const block = (key: string) => (
    <div key={key} className="mb-10 space-y-4">
      <div className="flex justify-end">
        <div className="h-11 w-[min(72%,18rem)] animate-pulse rounded-3xl bg-neutral-100" />
      </div>
      <div className="space-y-2.5 pl-1">
        <div className="h-3.5 w-[78%] max-w-xl animate-pulse rounded-md bg-neutral-100" />
        <div className="h-3.5 w-[58%] max-w-md animate-pulse rounded-md bg-neutral-100" />
        <div className="mt-3 h-28 w-full max-w-2xl animate-pulse rounded-2xl bg-neutral-50" />
      </div>
    </div>
  );
  return (
    <div className="space-y-2" aria-busy aria-label="Loading conversation">
      {block("a")}
      {block("b")}
    </div>
  );
}

function ChatMessageRow({
  m,
  busy,
  lastAssistant,
  serverChatSessionId,
  onRetry,
}: {
  m: ChatMessage;
  busy: boolean;
  lastAssistant: Extract<ChatMessage, { role: "assistant" }> | undefined;
  serverChatSessionId: string | null;
  onRetry?: () => void;
}) {
  const isLastAssistant = m.role === "assistant" && lastAssistant?.id === m.id;
  const streamCollapsed =
    m.role === "assistant" &&
    m.run.assistantBubbleMode === "step" &&
    busy &&
    isLastAssistant;
  const showFullAssistantMarkdown =
    m.role === "assistant" &&
    Boolean(m.run.assistantMarkdown.trim()) &&
    !streamCollapsed;
  /** Workspace file strip: only after this turn finishes (avoid live-updating during stream). */
  const showWorkspaceAttachments =
    m.role === "assistant" && !(busy && isLastAssistant);

  function saveAssistantToBrain(markdown: string) {
    try {
      const key = "koraku_brain_notes";
      const existing = JSON.parse(window.localStorage.getItem(key) || "[]");
      const list = Array.isArray(existing) ? existing : [];
      const title = markdown.split("\n").find((line) => line.trim())?.replace(/^#+\s*/, "").slice(0, 80) || "Saved Koraku note";
      const next = [
        {
          id: crypto.randomUUID(),
          title,
          body: markdown,
          createdAt: new Date().toISOString(),
        },
        ...list,
      ].slice(0, 100);
      window.localStorage.setItem(key, JSON.stringify(next));
    } catch {
      /* Local beta note storage is best-effort. */
    }
  }

  return m.role === "user" ? (
    <div className="mb-6 flex justify-end">
      <div className="max-w-[85%] space-y-2 rounded-3xl bg-neutral-100 px-4 py-3 text-[15px] font-medium text-koraku-ink">
        {m.images && m.images.length > 0 ? (
          <div className="flex flex-wrap justify-end gap-2">
            {m.images.map((im) => (
              <div
                key={im.id}
                className="h-28 w-28 overflow-hidden rounded-2xl border border-neutral-200/80 bg-white"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={im.previewUrl}
                  alt=""
                  className="h-full w-full object-cover"
                />
              </div>
            ))}
          </div>
        ) : null}
        {m.text ? <p className="whitespace-pre-wrap">{m.text}</p> : null}
      </div>
    </div>
  ) : (
    <div className="mb-10">
      <ToolTimeline
        rows={m.run.timeline}
        activeThought={m.run.activeThought}
        toolCallCount={m.run.toolInvocations}
        streamingExpand={busy && isLastAssistant}
      />
      {streamCollapsed ? (
        <p
          className="mb-2 truncate text-[13px] font-medium text-neutral-500"
          title={m.run.stepCaption ?? undefined}
        >
          {m.run.stepCaption?.trim()
            ? m.run.stepCaption
            : busy && isLastAssistant
              ? "…"
              : ""}
        </p>
      ) : null}
      {showFullAssistantMarkdown ? (
        <>
          <MarkdownBody
            source={m.run.assistantMarkdown}
            deferHeavyParse={busy && isLastAssistant}
          />
          <button
            type="button"
            onClick={() => saveAssistantToBrain(m.run.assistantMarkdown)}
            className="mt-3 rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-bold text-neutral-500 transition hover:border-neutral-300 hover:text-neutral-900"
          >
            Save to brain
          </button>
        </>
      ) : null}
      {showWorkspaceAttachments ? (
        <RunWorkspaceAttachments
          timeline={m.run.timeline}
          serverSessionId={serverChatSessionId}
        />
      ) : null}
      {busy && isLastAssistant ? (
        <AgentBusyRow startedAtMs={m.run.streamStartedAt!} />
      ) : null}
      {!m.run.assistantMarkdown.trim() && !busy && isLastAssistant ? (
        <p className="mt-2 text-sm text-neutral-400">No assistant text was returned.</p>
      ) : null}
      {m.run.error ? (
        <div className="mt-3 rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-800">
          <p>{m.run.error}</p>
          {onRetry && isLastAssistant && !busy ? (
            <button
              type="button"
              onClick={onRetry}
              className="mt-2 rounded-full border border-red-300 bg-white px-3 py-1 text-xs font-semibold text-red-700 hover:bg-red-100"
            >
              Retry
            </button>
          ) : null}
        </div>
      ) : null}
      {!(busy && isLastAssistant) ? (
        <p className="mt-4 text-[11px] font-semibold uppercase tracking-wide text-neutral-400">
          {m.run.statusText}
          {m.run.dropdownModelLabel && m.run.statusText !== "Done"
            ? ` · ${m.run.dropdownModelLabel}`
            : ""}
        </p>
      ) : null}
    </div>
  );
}

/** Main chat column; must render inside ``KorakuAppShell`` (provides chat context + chrome). */
export function ChatConversation() {
  const [workspaceOpen, setWorkspaceOpen] = useState(false);
  const [starterPrompts, setStarterPrompts] = useState<string[]>([]);
  const {
    hydrated,
    messagesLoadingSessionIds,
    activeId,
    messages,
    busy,
    queuedMessages,
    removeQueuedMessage,
    send,
    serverChatSessionByUi,
  } = useKorakuChatThread();

  const backendChatSessionId = serverChatSessionByUi[activeId] ?? null;

  const chatMainLoading =
    !hydrated ||
    (Boolean(activeId) && messagesLoadingSessionIds.includes(activeId));

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem("koraku_starter_prompts");
      if (!raw) {
        setStarterPrompts([
          "Remember how I like to work and ask three setup questions.",
          "Create a second-brain note for my current priorities.",
          "Suggest one useful daily automation I can safely try.",
        ]);
        return;
      }
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        setStarterPrompts(parsed.filter((p): p is string => typeof p === "string").slice(0, 3));
      }
    } catch {
      setStarterPrompts([]);
    }
  }, []);

  const lastAssistant = useMemo((): Extract<ChatMessage, { role: "assistant" }> | undefined => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i]!;
      if (m.role === "assistant") return m;
    }
    return undefined;
  }, [messages]);

  const retryLastTurn = useMemo(() => {
    return () => {
      if (busy) return;
      for (let i = messages.length - 1; i >= 0; i--) {
        const m = messages[i]!;
        if (m.role === "user" && m.text.trim()) {
          send(m.text, "", "", "");
          return;
        }
      }
    };
  }, [busy, messages, send]);

  const scrollParentRef = useRef<HTMLDivElement>(null);
  const virtualEnabled =
    !chatMainLoading && messages.length >= VIRTUALIZE_MESSAGE_COUNT;

  const rowVirtualizer = useVirtualizer({
    count: virtualEnabled ? messages.length : 0,
    getScrollElement: () => scrollParentRef.current,
    estimateSize: (index) => (messages[index]?.role === "user" ? 100 : 260),
    overscan: 6,
    getItemKey: (index) => messages[index]?.id ?? index,
  });

  useLayoutEffect(() => {
    if (!busy || chatMainLoading || messages.length === 0) return;
    const el = scrollParentRef.current;
    if (!el) return;
    const threshold = 180;
    const { scrollTop, scrollHeight, clientHeight } = el;
    if (scrollHeight - scrollTop - clientHeight < threshold) {
      el.scrollTop = scrollHeight;
    }
  }, [messages, busy, chatMainLoading]);

  return (
    <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white">
      <div
        className={clsx(
          "flex min-h-0 flex-1 flex-row overflow-hidden",
          workspaceOpen && "gap-2 pr-2 pt-2 pb-2",
        )}
      >
        <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          <div className="flex shrink-0 items-center justify-end gap-3 border-b border-neutral-100/90 bg-white/90 px-4 py-2">
            <button
              type="button"
              onClick={() => setWorkspaceOpen((o) => !o)}
              aria-pressed={workspaceOpen}
              className={clsx(
                "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold shadow-sm transition-colors",
                workspaceOpen
                  ? "border-neutral-300 bg-neutral-100 text-koraku-ink"
                  : "border-neutral-200 bg-white text-koraku-ink hover:bg-neutral-50",
              )}
            >
              <PanelRight
                className={clsx(
                  "h-3.5 w-3.5",
                  workspaceOpen ? "text-koraku-ink" : "text-neutral-500",
                )}
                aria-hidden
              />
              Workspace
            </button>
          </div>

          <div
            ref={scrollParentRef}
            className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain"
          >
            <div className="mx-auto max-w-3xl px-4 py-8 pb-6">
              {chatMainLoading ? (
                <ChatMessagesSkeleton />
              ) : (
                <>
                  {messages.length === 0 && (
                    <div className="py-16 text-center">
                      <div className="mx-auto mb-5 flex justify-center">
                        <BrandMark size={88} priority variant="newChat" />
                      </div>
                      <h1 className="text-2xl font-bold tracking-tight text-koraku-ink">
                        What should we move forward today?
                      </h1>
                      <p className="mt-2 text-sm font-medium text-koraku-muted">
                        Koraku can remember preferences, organize your second brain,
                        and set up safe automations.
                      </p>
                      {starterPrompts.length > 0 ? (
                        <div className="mx-auto mt-6 grid max-w-2xl gap-2 text-left sm:grid-cols-3">
                          {starterPrompts.map((prompt) => (
                            <button
                              key={prompt}
                              type="button"
                              onClick={() => send(prompt, "", "", "")}
                              className="rounded-2xl border border-neutral-200 bg-white px-4 py-3 text-left text-xs font-semibold leading-relaxed text-neutral-700 shadow-sm transition hover:-translate-y-0.5 hover:border-neutral-300 hover:text-neutral-950"
                            >
                              {prompt}
                            </button>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  )}

                  {virtualEnabled ? (
                    <div
                      className="relative w-full"
                      style={{ height: rowVirtualizer.getTotalSize() }}
                    >
                      {rowVirtualizer.getVirtualItems().map((vi) => {
                        const m = messages[vi.index]!;
                        return (
                          <div
                            key={vi.key}
                            data-index={vi.index}
                            ref={rowVirtualizer.measureElement}
                            className="left-0 top-0 w-full pb-0"
                            style={{
                              position: "absolute",
                              transform: `translateY(${vi.start}px)`,
                            }}
                          >
                            <ChatMessageRow
                              m={m}
                              busy={busy}
                              lastAssistant={lastAssistant}
                              serverChatSessionId={backendChatSessionId}
                              onRetry={retryLastTurn}
                            />
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    messages.map((m) => (
                      <ChatMessageRow
                        key={m.id}
                        m={m}
                        busy={busy}
                        lastAssistant={lastAssistant}
                        serverChatSessionId={backendChatSessionId}
                        onRetry={retryLastTurn}
                      />
                    ))
                  )}
                </>
              )}
            </div>
          </div>

          <div
            className={clsx(
              "shrink-0 bg-white/65 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-3 backdrop-blur-2xl backdrop-saturate-150",
              chatMainLoading && "pointer-events-none opacity-60",
            )}
          >
            <MessageQueueBar items={queuedMessages} onRemove={removeQueuedMessage} />
            <Composer
              busy={busy}
              disabled={chatMainLoading}
              placeholder={busy ? "Give Koraku a follow-up…" : "Ask anything"}
              onSend={send}
            />
          </div>
        </section>

        <WorkspacePanel
          visible={workspaceOpen}
          onClose={() => setWorkspaceOpen(false)}
          serverSessionId={backendChatSessionId}
        />
      </div>
    </main>
  );
}
