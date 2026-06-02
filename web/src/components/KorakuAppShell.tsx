"use client";

import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { KorakuChatProvider } from "@/context/KorakuChatContext";
import { useKorakuChat } from "@/hooks/useKorakuChat";
import { APP_BASE, isAppChatRoute } from "@/lib/app-path";
import { AppChrome } from "@/components/AppChrome";
import { ChatConversation } from "@/components/ChatApp";
import { SetupStatusBanner } from "@/components/SetupStatusBanner";

export function KorakuAppShell({ children }: { children: ReactNode }) {
  const chat = useKorakuChat();
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname() || "";
  const router = useRouter();

  const onSelectSession = useCallback(
    (id: string) => {
      chat.shell.selectSession(id);
      if (!isAppChatRoute(pathname)) {
        router.push(APP_BASE);
      }
    },
    [chat, pathname, router],
  );

  const onNewChat = useCallback(async () => {
    await chat.shell.newChat();
    if (!isAppChatRoute(pathname)) {
      router.push(APP_BASE);
    }
  }, [chat, pathname, router]);

  const onDeleteChat = useCallback(async (id: string) => {
    await chat.shell.deleteSession(id);
  }, [chat]);

  const onRefreshChat = useCallback(
    async (id: string) => {
      await chat.shell.refreshSession(id);
      if (chat.shell.activeId === id && !isAppChatRoute(pathname)) {
        router.push(APP_BASE);
      }
    },
    [chat, pathname, router],
  );

  useEffect(() => {
    void fetch("/api/org/current", { method: "POST" }).catch(() => {});
  }, []);

  const prevPathRef = useRef(pathname);
  useEffect(() => {
    const prev = prevPathRef.current;
    prevPathRef.current = pathname;
    if (isAppChatRoute(prev) && !isAppChatRoute(pathname)) {
      void chat.shell.discardEmptyActiveSession();
    }
  }, [pathname, chat.shell]);

  return (
    <KorakuChatProvider shell={chat.shell} thread={chat.thread}>
      <SetupStatusBanner />
      <AppChrome
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((c) => !c)}
        chatsLoading={!chat.shell.hydrated}
        sessions={chat.shell.sessions}
        activeId={chat.shell.activeId}
        streamingSessionIds={chat.shell.streamingSessionIds}
        deletingSessionIds={chat.shell.deletingSessionIds}
        refreshingSessionIds={chat.shell.refreshingSessionIds}
        onSelectSession={onSelectSession}
        onNewChat={onNewChat}
        onDeleteChat={onDeleteChat}
        onRefreshChat={onRefreshChat}
      >
        {isAppChatRoute(pathname) ? <ChatConversation /> : children}
      </AppChrome>
    </KorakuChatProvider>
  );
}
