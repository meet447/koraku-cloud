"use client";

import {
  memo,
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import { KorakuChatProviderWithState } from "@/components/KorakuChatProviderWithState";
import { useKorakuChatShell } from "@/context/KorakuChatContext";
import {
  APP_BASE,
  isAppChatRoute,
  isAppRoute,
  isOnboardingRoute,
  ONBOARDING_PATH,
} from "@/lib/app-path";
import { loadPersonalization } from "@/lib/koraku-personalization";
import {
  hasPersonalizationOnboardingProfile,
  isOnboardingComplete,
  markOnboardingComplete,
} from "@/lib/onboarding";
import { AppChrome } from "@/components/AppChrome";
import { ChatConversation } from "@/components/ChatApp";
import { SetupStatusBanner } from "@/components/SetupStatusBanner";

function OnboardingGate({ children }: { children: ReactNode }) {
  const pathname = usePathname() || "";
  const router = useRouter();
  const [complete, setComplete] = useState<boolean | null>(null);

  useLayoutEffect(() => {
    if (isOnboardingComplete()) {
      setComplete(true);
    }
  }, []);

  useEffect(() => {
    if (complete !== null) return;
    let cancelled = false;
    void loadPersonalization()
      .then((data) => {
        if (cancelled) return;
        const profileComplete = hasPersonalizationOnboardingProfile(data.memory);
        if (profileComplete) markOnboardingComplete();
        setComplete(profileComplete);
      })
      .catch(() => {
        if (!cancelled) setComplete(false);
      });
    return () => {
      cancelled = true;
    };
  }, [complete]);

  const onOnboarding = isOnboardingRoute(pathname);
  const inApp = isAppRoute(pathname);
  const resolving = complete === null;

  if (!resolving) {
    if (onOnboarding && complete) {
      router.replace(APP_BASE);
      return (
        <div className="flex h-[100dvh] items-center justify-center bg-white text-sm font-medium text-neutral-500">
          Loading…
        </div>
      );
    }
    if (inApp && !onOnboarding && !complete) {
      router.replace(ONBOARDING_PATH);
      return (
        <div className="flex h-[100dvh] items-center justify-center bg-white text-sm font-medium text-neutral-500">
          Loading…
        </div>
      );
    }
  }

  if (resolving) {
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
    return (
      <div className="flex h-[100dvh] items-center justify-center bg-white text-sm font-medium text-neutral-500">
        Loading…
      </div>
    );
  }

  return <>{children}</>;
}

const RouteOutlet = memo(function RouteOutlet({ children }: { children: ReactNode }) {
  return children;
});

const ProductShellFrame = memo(function ProductShellFrame({
  routeChildren,
}: {
  routeChildren: ReactNode;
}) {
  const shell = useKorakuChatShell();
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname() || "";
  const router = useRouter();

  const onSelectSession = useCallback(
    (id: string) => {
      shell.selectSession(id);
      if (!isAppChatRoute(pathname)) {
        router.push(APP_BASE);
      }
    },
    [shell, pathname, router],
  );

  const onNewChat = useCallback(async () => {
    await shell.newChat();
    if (!isAppChatRoute(pathname)) {
      router.push(APP_BASE);
    }
  }, [shell, pathname, router]);

  const onDeleteChat = useCallback(
    async (id: string) => {
      await shell.deleteSession(id);
    },
    [shell],
  );

  const onRefreshChat = useCallback(
    async (id: string) => {
      await shell.refreshSession(id);
      if (shell.activeId === id && !isAppChatRoute(pathname)) {
        router.push(APP_BASE);
      }
    },
    [shell, pathname, router],
  );

  const prevPathRef = useRef(pathname);
  useEffect(() => {
    const prev = prevPathRef.current;
    prevPathRef.current = pathname;
    if (isAppChatRoute(prev) && !isAppChatRoute(pathname)) {
      void shell.discardEmptyActiveSession();
    }
  }, [pathname, shell]);

  return (
    <>
      <SetupStatusBanner />
      <AppChrome
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((c) => !c)}
        onSelectSession={onSelectSession}
        onNewChat={onNewChat}
        onDeleteChat={onDeleteChat}
        onRefreshChat={onRefreshChat}
      >
        {isAppChatRoute(pathname) ? <ChatConversation /> : <RouteOutlet>{routeChildren}</RouteOutlet>}
      </AppChrome>
    </>
  );
});

function ProductShell({ children }: { children: ReactNode }) {
  return (
    <KorakuChatProviderWithState>
      <ProductShellFrame routeChildren={children} />
    </KorakuChatProviderWithState>
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
