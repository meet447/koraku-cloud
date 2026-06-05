"use client";

import Image from "next/image";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useLayoutEffect, useMemo, useRef, useState } from "react";
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
import { NewChatLocalContext } from "./NewChatLocalContext";
import dynamic from "next/dynamic";

const WorkspacePanel = dynamic(
  () => import("./WorkspacePanel").then((mod) => mod.WorkspacePanel),
  {
    ssr: false,
  }
);
import { RunWorkspaceAttachments } from "./RunWorkspaceAttachments";
import { StreamingReplySkeleton } from "./StreamingReplySkeleton";
import { initialRunState } from "@/lib/korakuReducer";
import { shouldShowRunFooterStatus } from "@/lib/runStatusText";
import { readStarterPrompts } from "@/lib/starter-prompts";
import { ChatMessagesSkeleton } from "@/components/ChatMessagesSkeleton";

/** Use windowed rendering when a thread has at least this many rows. */
const VIRTUALIZE_MESSAGE_COUNT = 10;

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
  if (m.role === "user") {
    return (
      <div className="mb-6 flex justify-end">
        <div className="max-w-[85%] space-y-2 rounded-3xl bg-neutral-100 px-4 py-3 text-[15px] font-medium text-koraku-ink">
          {m.images && m.images.length > 0 ? (
            <div className="flex flex-wrap justify-end gap-2">
              {m.images.map((im) => (
                <div
                  key={im.id}
                  className="h-28 w-28 overflow-hidden rounded-2xl border border-neutral-200/80 bg-white"
                >
                  <Image
                    src={im.previewUrl}
                    alt=""
                    width={112}
                    height={112}
                    unoptimized
                    className="h-full w-full object-cover"
                  />
                </div>
              ))}
            </div>
          ) : null}
          {m.text ? <p className="whitespace-pre-wrap">{m.text}</p> : null}
        </div>
      </div>
    );
  }

  const run = m.run ?? initialRunState();
  const isLastAssistant = lastAssistant?.id === m.id;
  const streamCollapsed =
    run.assistantBubbleMode === "step" && busy && isLastAssistant;
  const showFullAssistantMarkdown =
    Boolean(run.assistantMarkdown.trim()) && !streamCollapsed;
  /** Workspace file strip: only after this turn finishes (avoid live-updating during stream). */
  const showWorkspaceAttachments = !(busy && isLastAssistant);

  const showStreamingSkeleton =
    busy &&
    isLastAssistant &&
    !run.assistantMarkdown.trim() &&
    run.timeline.length === 0 &&
    !run.activeThought;

  const showRunFooter =
    shouldShowRunFooterStatus(run.statusText) ||
    (run.error != null && run.error.length > 0);

  return (
    <div className="mb-10">
      <ToolTimeline
        rows={run.timeline}
        activeThought={run.activeThought}
        toolCallCount={run.toolInvocations}
        streamingExpand={busy && isLastAssistant}
      />
      {streamCollapsed ? (
        <p
          className="mb-2 truncate text-[13px] font-medium text-neutral-500"
          title={run.stepCaption ?? undefined}
        >
          {run.stepCaption?.trim()
            ? run.stepCaption
            : busy && isLastAssistant
              ? "…"
              : ""}
        </p>
      ) : null}
      {showStreamingSkeleton ? <StreamingReplySkeleton /> : null}
      {showFullAssistantMarkdown ? (
        <MarkdownBody
          source={run.assistantMarkdown}
          deferHeavyParse={busy && isLastAssistant}
        />
      ) : null}
      {showWorkspaceAttachments ? (
        <RunWorkspaceAttachments
          timeline={run.timeline}
          serverSessionId={serverChatSessionId}
        />
      ) : null}
      {busy && isLastAssistant ? (
        <AgentBusyRow
          startedAtMs={run.streamStartedAt!}
          statusText={run.statusText}
        />
      ) : null}
      {!run.assistantMarkdown.trim() && !busy && isLastAssistant ? (
        <p className="mt-2 text-sm text-neutral-400">
          {run.statusText?.includes("Reconnect") ||
          run.statusText?.includes("Subscribe") ||
          run.error
            ? "This reply was interrupted (for example after a page refresh). Use Retry or send your message again."
            : "No assistant text was returned."}
        </p>
      ) : null}
      {run.error ? (
        <div className="mt-3 rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-800">
          <p>{run.error}</p>
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
      {showRunFooter ? (
        <p className="mt-4 text-[11px] font-semibold uppercase tracking-wide text-neutral-400">
          {run.statusText}
          {run.dropdownModelLabel && run.statusText === "Done"
            ? ` · ${run.dropdownModelLabel}`
            : ""}
        </p>
      ) : null}
    </div>
  );
}

/** Main chat column; must render inside ``KorakuAppShell`` (provides chat context + chrome). */
export function ChatConversation() {
  const [workspaceOpen, setWorkspaceOpen] = useState(false);
  const [starterPrompts] = useState(readStarterPrompts);
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
    workspaceRefreshToken,
  } = useKorakuChatThread();

  const backendChatSessionId = serverChatSessionByUi[activeId] ?? null;

  const chatMainLoading =
    !hydrated ||
    (Boolean(activeId) && messagesLoadingSessionIds.includes(activeId));

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
          <div className="flex shrink-0 items-center justify-end gap-3 border-b border-neutral-200/50 bg-white px-4 py-2">
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

          <div className="relative min-h-0 flex-1">
            <div
              ref={scrollParentRef}
              className="absolute inset-0 overflow-y-auto overscroll-y-contain"
            >
            <div className="mx-auto max-w-3xl px-4 py-8 pb-36">
              {chatMainLoading ? (
                <ChatMessagesSkeleton />
              ) : (
                <>
                  {messages.length === 0 && (
                    <div className="py-16 text-center">
                      <div className="mx-auto mb-5 flex justify-center">
                        <BrandMark size={88} priority variant="newChat" />
                      </div>
                      <NewChatLocalContext />
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
                "pointer-events-none absolute inset-x-0 bottom-0 z-10 flex flex-col bg-gradient-to-t from-white from-40% via-white/90 to-transparent pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-10",
                chatMainLoading && "opacity-60",
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
          </div>
        </section>

        <WorkspacePanel
          visible={workspaceOpen}
          onClose={() => setWorkspaceOpen(false)}
          serverSessionId={backendChatSessionId}
          workspaceRefreshToken={workspaceRefreshToken}
        />
      </div>
    </main>
  );
}
