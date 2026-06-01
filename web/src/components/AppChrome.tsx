"use client";

import { Sidebar } from "./Sidebar";
import type { ChatSession } from "@/hooks/useKorakuChat";

export function AppChrome({
  collapsed,
  onToggleCollapse,
  chatsLoading = false,
  sessions,
  activeId,
  streamingSessionIds = [],
  deletingSessionIds = [],
  onSelectSession,
  onNewChat,
  onDeleteChat,
  children,
}: {
  collapsed: boolean;
  onToggleCollapse: () => void;
  chatsLoading?: boolean;
  sessions: ChatSession[];
  activeId: string;
  streamingSessionIds?: string[];
  deletingSessionIds?: string[];
  onSelectSession: (id: string) => void;
  onNewChat: () => void | Promise<void>;
  onDeleteChat: (id: string) => void | Promise<void>;
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-[100dvh] w-full overflow-hidden bg-white text-koraku-ink">
      <div className="box-border flex h-full shrink-0 rounded-[28px] bg-white p-2 pr-2">
        <Sidebar
          collapsed={collapsed}
          onToggleCollapse={onToggleCollapse}
          chatsLoading={chatsLoading}
          sessions={sessions}
          activeId={activeId}
          streamingSessionIds={streamingSessionIds}
          deletingSessionIds={deletingSessionIds}
          onSelectSession={onSelectSession}
          onNewChat={onNewChat}
          onDeleteChat={onDeleteChat}
        />
      </div>
      <div className="relative flex min-h-0 min-w-0 flex-1 flex-col bg-white">
        {children}
      </div>
    </div>
  );
}
