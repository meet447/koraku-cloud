"use client";

import { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import clsx from "clsx";
import { Sidebar } from "./Sidebar";
import { useKorakuChatShell } from "@/context/KorakuChatContext";

export function AppChrome({
  collapsed,
  onToggleCollapse,
  onSelectSession,
  onNewChat,
  onDeleteChat,
  onRefreshChat,
  children,
}: {
  collapsed: boolean;
  onToggleCollapse: () => void;
  onSelectSession: (id: string) => void;
  onNewChat: () => void | Promise<void>;
  onDeleteChat: (id: string) => void | Promise<void>;
  onRefreshChat: (id: string) => void | Promise<void>;
  children: React.ReactNode;
}) {
  const shell = useKorakuChatShell();
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname() || "";

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const handleSelectSessionMobile = (id: string) => {
    onSelectSession(id);
    setMobileOpen(false);
  };

  const handleNewChatMobile = async () => {
    await onNewChat();
    setMobileOpen(false);
  };

  return (
    <div className="relative flex h-[100dvh] w-full overflow-hidden bg-white text-koraku-ink">
      <div
        className={clsx(
          "box-border h-full shrink-0 bg-transparent p-2 pr-1 transition-transform duration-300 ease-out md:relative md:z-auto md:flex md:bg-white",
          "fixed inset-y-0 left-0 z-50",
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
      >
        <Sidebar
          collapsed={collapsed}
          onToggleCollapse={onToggleCollapse}
          chatsLoading={!shell.hydrated}
          sessions={shell.sessions}
          activeId={shell.activeId}
          streamingSessionIds={shell.streamingSessionIds}
          deletingSessionIds={shell.deletingSessionIds}
          refreshingSessionIds={shell.refreshingSessionIds}
          onSelectSession={handleSelectSessionMobile}
          onNewChat={handleNewChatMobile}
          onDeleteChat={onDeleteChat}
          onRefreshChat={onRefreshChat}
          onCloseMobile={() => setMobileOpen(false)}
        />
      </div>

      {mobileOpen ? (
        <div
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 z-40 bg-neutral-950/20 backdrop-blur-[2px] transition-opacity duration-300 md:hidden"
        />
      ) : null}

      <div className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-neutral-100 bg-white px-4 md:hidden">
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="flex h-9 w-9 items-center justify-center rounded-full text-neutral-500 hover:bg-neutral-50 hover:text-neutral-900 active:bg-neutral-100"
              aria-label="Open sidebar"
              title="Open sidebar"
            >
              <Menu className="h-5 w-5" strokeWidth={1.5} />
            </button>
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-bold tracking-tight text-neutral-900">
                Koraku
              </span>
            </div>
          </div>
        </header>

        {children}
      </div>
    </div>
  );
}
