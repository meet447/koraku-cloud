"use client";

import {
  memo,
  useCallback,
  useEffect,
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
import {
  invalidatePersonalizationCache,
  loadPersonalization,
} from "@/lib/koraku-personalization";
import {
  clearOnboardingClientState,
  hasPersonalizationOnboardingProfile,
  isOnboardingComplete,
  markOnboardingComplete,
  ONBOARDING_COMPLETE_EVENT,
  ONBOARDING_RESET_EVENT,
} from "@/lib/onboarding";
import { AppChrome } from "@/components/AppChrome";
import { ChatConversation } from "@/components/ChatApp";
import { KorakuAppLoading } from "@/components/KorakuAppLoading";
import { SetupStatusBanner } from "@/components/SetupStatusBanner";

function OnboardingGate({ children }: { children: ReactNode }) {
  const pathname = usePathname() || "";
  const router = useRouter();
  const [complete, setComplete] = useState<boolean | null>(null);
  const [checkNonce, setCheckNonce] = useState(0);
  const gateResolvedRef = useRef(false);

  useEffect(() => {
    const onDone = () => {
      gateResolvedRef.current = true;
      setComplete(true);
    };
    const onReset = () => {
      gateResolvedRef.current = false;
      invalidatePersonalizationCache();
      setComplete(null);
      setCheckNonce((n) => n + 1);
    };
    window.addEventListener(ONBOARDING_COMPLETE_EVENT, onDone);
    window.addEventListener(ONBOARDING_RESET_EVENT, onReset);
    return () => {
      window.removeEventListener(ONBOARDING_COMPLETE_EVENT, onDone);
      window.removeEventListener(ONBOARDING_RESET_EVENT, onReset);
    };
  }, []);

  useEffect(() => {
    if (gateResolvedRef.current && isOnboardingComplete()) {
      setComplete(true);
      return;
    }

    let cancelled = false;
    void loadPersonalization({ force: !gateResolvedRef.current })
      .then((data) => {
        if (cancelled) return;
        gateResolvedRef.current = true;
        const profileComplete = hasPersonalizationOnboardingProfile(data.memory);
        if (profileComplete) {
          markOnboardingComplete();
          setComplete(true);
          return;
        }
        clearOnboardingClientState();
        setComplete(false);
      })
      .catch(() => {
        if (cancelled) return;
        gateResolvedRef.current = true;
        clearOnboardingClientState();
        setComplete(false);
      });
    return () => {
      cancelled = true;
    };
  }, [pathname, checkNonce]);

  const onOnboarding = isOnboardingRoute(pathname);
  const inApp = isAppRoute(pathname);
  const resolving = complete === null;
  const redirectToApp = !resolving && onOnboarding && complete;
  const redirectToOnboarding = !resolving && inApp && !onOnboarding && !complete;

  useEffect(() => {
    if (redirectToApp) {
      router.replace(APP_BASE);
      return;
    }
    if (redirectToOnboarding) {
      router.replace(ONBOARDING_PATH);
    }
  }, [redirectToApp, redirectToOnboarding, router]);

  if (resolving || redirectToApp || redirectToOnboarding) {
    return <KorakuAppLoading />;
  }

  if (onOnboarding) {
    return <div className="h-[100dvh] overflow-y-auto bg-white text-koraku-ink">{children}</div>;
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
