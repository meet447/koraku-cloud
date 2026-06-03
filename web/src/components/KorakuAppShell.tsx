"use client";

import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { KorakuChatProvider } from "@/context/KorakuChatContext";
import { useKorakuChat } from "@/hooks/useKorakuChat";
import {
  APP_BASE,
  isAppChatRoute,
  isAppRoute,
  isOnboardingRoute,
  ONBOARDING_PATH,
} from "@/lib/app-path";
import { isOnboardingComplete } from "@/lib/onboarding";
import { AppChrome } from "@/components/AppChrome";
import { ChatConversation } from "@/components/ChatApp";
import { SetupStatusBanner } from "@/components/SetupStatusBanner";

function OnboardingGate({ children }: { children: ReactNode }) {
  const pathname = usePathname() || "";
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setReady(true);
  }, []);

  const complete = isOnboardingComplete();
  const onOnboarding = isOnboardingRoute(pathname);
  const inApp = isAppRoute(pathname);

  useEffect(() => {
    if (!ready) return;
    if (onOnboarding && complete) {
      router.replace(APP_BASE);
      return;
    }
    if (inApp && !onOnboarding && !complete) {
      router.replace(ONBOARDING_PATH);
    }
  }, [ready, onOnboarding, inApp, complete, router]);

  if (!ready) {
    return (
      <div className="flex h-[100dvh] items-center justify-center bg-white text-sm font-medium text-neutral-500">
        Loading…
      </div>
    );
  }

  if (onOnboarding) {
    if (complete) {
      return null;
    }
    return <div className="h-[100dvh] overflow-y-auto bg-white text-koraku-ink">{children}</div>;
  }

  if (inApp && !complete) {
    return null;
  }

  return <>{children}</>;
}

function ProductShell({ children }: { children: ReactNode }) {
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

export function KorakuAppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname() || "";
  const onOnboarding = isOnboardingRoute(pathname);

  return (
    <OnboardingGate>
      {onOnboarding ? children : <ProductShell>{children}</ProductShell>}
    </OnboardingGate>
  );
}
