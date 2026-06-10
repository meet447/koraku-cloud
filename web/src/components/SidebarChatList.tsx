"use client";

import { useMemo, useRef, useState } from "react";
import {
  Loader2,
  MessageCircle,
  RefreshCw,
  Search,
  Trash2,
} from "lucide-react";
import clsx from "clsx";
import type { ChatSession } from "@/hooks/useKorakuChat";
import { sortChatSessions } from "@/lib/chat-sessions";

const iconStroke = 1.5;
const CHAT_SKELETON_KEYS = ["a", "b", "c", "d", "e", "f"] as const;
const CHAT_SKELETON_WIDTHS = ["w-[88%]", "w-[72%]", "w-[80%]", "w-[64%]", "w-[76%]", "w-[56%]"] as const;

export function SidebarChatList({
  chatsLoading,
  sessions,
  activeId,
  streamingSessionIds,
  deletingSessionIds,
  refreshingSessionIds,
  onSelectSession,
  onDeleteChat,
  onRefreshChat,
}: {
  chatsLoading: boolean;
  sessions: ChatSession[];
  activeId: string;
  streamingSessionIds: string[];
  deletingSessionIds: string[];
  refreshingSessionIds: string[];
  onSelectSession: (id: string) => void;
  onDeleteChat: (id: string) => void | Promise<void>;
  onRefreshChat: (id: string) => void | Promise<void>;
}) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);
  const streamingSet = new Set(streamingSessionIds);
  const deletingSet = new Set(deletingSessionIds);
  const refreshingSet = new Set(refreshingSessionIds);
  const visibleSessions = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = q
      ? sessions.filter((s) => s.title.toLowerCase().includes(q))
      : sessions;
    return sortChatSessions(list);
  }, [query, sessions]);

  return (
    <div className="mt-4 flex min-h-0 flex-1 flex-col">
      <div className="mb-2 flex shrink-0 items-center justify-between px-1">
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-400">
          Chats
        </span>
        <button
          type="button"
          onClick={() => {
            setSearchOpen((o) => {
              const next = !o;
              if (next) {
                queueMicrotask(() => searchInputRef.current?.focus());
              }
              return next;
            });
          }}
          className="rounded-md p-1 text-neutral-400 transition hover:bg-white/80 hover:text-neutral-600"
          aria-label="Search chats"
          title="Search chats"
        >
          <Search className="h-3.5 w-3.5" strokeWidth={iconStroke} />
        </button>
      </div>
      {searchOpen ? (
        <input
          ref={searchInputRef}
          id="sidebar-chat-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search chats..."
          aria-label="Search chats"
          className="mb-2 w-full rounded-2xl border border-neutral-200 bg-white px-3 py-2 text-[13px] font-medium text-neutral-800 outline-none placeholder:text-neutral-400 focus:ring-2 focus:ring-neutral-200"
        />
      ) : null}
      <div
        className="min-h-0 flex-1 space-y-0.5 overflow-y-auto overflow-x-hidden pr-0.5"
        aria-busy={chatsLoading}
        aria-label={chatsLoading ? "Loading chats" : undefined}
      >
        {chatsLoading ? (
          <div className="space-y-0.5">
            {CHAT_SKELETON_KEYS.map((key, i) => (
              <div
                key={key}
                className="flex w-full min-w-0 items-center gap-2 rounded-[1.1rem] px-2.5 py-2"
                aria-hidden
              >
                <span className="h-3.5 w-3.5 shrink-0 rounded bg-neutral-200/80" />
                <span
                  className={clsx(
                    "h-3.5 shrink-0 rounded-lg bg-neutral-200/80 animate-pulse",
                    CHAT_SKELETON_WIDTHS[i],
                  )}
                />
              </div>
            ))}
          </div>
        ) : visibleSessions.length === 0 ? (
          <p className="px-2.5 py-3 text-xs font-medium text-neutral-400">
            {query.trim() ? "No matching chats." : "No chats yet."}
          </p>
        ) : (
          visibleSessions.map((s) => {
            const deleting = deletingSet.has(s.id);
            const refreshing = refreshingSet.has(s.id);
            const isImessage = s.channel === "imessage" || s.pinned;
            return (
              <div
                key={s.id}
                aria-busy={deleting || refreshing}
                className={clsx(
                  "group flex w-full min-w-0 items-center gap-0.5 rounded-[1.1rem] py-1.5 pl-2.5 pr-1 transition",
                  s.id === activeId
                    ? "bg-white text-neutral-900 shadow-sm ring-1 ring-neutral-200/60"
                    : "text-neutral-600 hover:bg-white/70 hover:text-neutral-900",
                  (deleting || refreshing) && "opacity-70",
                )}
              >
                <button
                  type="button"
                  disabled={deleting || refreshing}
                  onClick={() => onSelectSession(s.id)}
                  className="flex min-w-0 flex-1 items-center gap-2 rounded-lg py-0.5 text-left text-[13px] font-medium disabled:cursor-wait"
                >
                  {deleting || refreshing ? (
                    <Loader2
                      className="h-3.5 w-3.5 shrink-0 animate-spin text-neutral-500"
                      aria-hidden
                    />
                  ) : streamingSet.has(s.id) ? (
                    <Loader2
                      className="h-3.5 w-3.5 shrink-0 animate-spin text-neutral-400"
                      aria-hidden
                    />
                  ) : isImessage ? (
                    <MessageCircle
                      className="h-3.5 w-3.5 shrink-0 text-violet-500"
                      aria-hidden
                    />
                  ) : (
                    <span className="h-3.5 w-3.5 shrink-0" aria-hidden />
                  )}
                  <span className="min-w-0 flex-1 truncate">{s.title}</span>
                </button>
                {isImessage ? (
                  <button
                    type="button"
                    disabled={refreshing || deleting}
                    onClick={(e) => {
                      e.stopPropagation();
                      void onRefreshChat(s.id);
                    }}
                    className={clsx(
                      "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-neutral-400 transition",
                      "hover:bg-violet-50 hover:text-violet-700 disabled:pointer-events-none disabled:opacity-100",
                      refreshing
                        ? "opacity-100"
                        : "opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100",
                    )}
                    aria-label={
                      refreshing
                        ? `Refreshing chat: ${s.title}`
                        : `Refresh iMessage history: ${s.title}`
                    }
                    title={refreshing ? "Refreshing…" : "Refresh from iMessage"}
                  >
                    <RefreshCw
                      className={clsx(
                        "h-3.5 w-3.5",
                        refreshing && "animate-spin text-violet-600",
                      )}
                      strokeWidth={iconStroke}
                      aria-hidden
                    />
                  </button>
                ) : (
                  <button
                    type="button"
                    disabled={deleting}
                    onClick={(e) => {
                      e.stopPropagation();
                      void onDeleteChat(s.id);
                    }}
                    className={clsx(
                      "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-neutral-400 transition",
                      "hover:bg-red-50 hover:text-red-600 disabled:pointer-events-none disabled:opacity-100",
                      deleting
                        ? "opacity-100"
                        : "opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100",
                    )}
                    aria-label={
                      deleting ? `Deleting chat: ${s.title}` : `Delete chat: ${s.title}`
                    }
                    title={deleting ? "Deleting…" : "Delete chat"}
                  >
                    <Trash2
                      className={clsx(
                        "h-3.5 w-3.5",
                        deleting && "animate-pulse text-neutral-400",
                      )}
                      strokeWidth={iconStroke}
                      aria-hidden
                    />
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
