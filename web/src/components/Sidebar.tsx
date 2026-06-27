"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import {
  Network,
  PanelLeftClose,
  PanelLeft,
  MessageCircle,
  Plug,
  Plus,
  Settings2,
  Wand2,
  X,
} from "lucide-react";
import clsx from "clsx";
import type { ChatSession } from "@/hooks/useKorakuChat";
import { BrandMark } from "@/components/BrandMark";
import { AccountMenu } from "@/components/AccountMenu";
import { APP_BASE } from "@/lib/app-path";
import { isSettingsRoute, SETTINGS_PANEL_HREF } from "@/lib/settings-panel";
import { SidebarSettingsMenu } from "@/components/SidebarSettingsMenu";
import { SidebarChatList } from "@/components/SidebarChatList";
import { EMPTY_STRING_ARRAY } from "@/lib/empty-arrays";

const iconStroke = 1.5;

const nav = [
  { label: "New chat", icon: Plus, accent: true },
  { href: `${APP_BASE}/memory`, label: "Memory", icon: Network },
  { href: `${APP_BASE}/connections`, label: "Connections", icon: Plug },
  { href: `${APP_BASE}/external`, label: "External", icon: MessageCircle },
  { href: `${APP_BASE}/automations`, label: "Habits", icon: Wand2 },
];

export function Sidebar({
  collapsed,
  onToggleCollapse,
  chatsLoading = false,
  sessions,
  activeId,
  streamingSessionIds,
  deletingSessionIds = EMPTY_STRING_ARRAY,
  refreshingSessionIds = EMPTY_STRING_ARRAY,
  onSelectSession,
  onNewChat,
  onDeleteChat,
  onRefreshChat,
  onCloseMobile,
}: {
  collapsed: boolean;
  onToggleCollapse: () => void;
  chatsLoading?: boolean;
  sessions: ChatSession[];
  activeId: string;
  streamingSessionIds: string[];
  deletingSessionIds?: string[];
  refreshingSessionIds?: string[];
  onSelectSession: (id: string) => void;
  onNewChat: () => void | Promise<void>;
  onDeleteChat: (id: string) => void | Promise<void>;
  onRefreshChat: (id: string) => void | Promise<void>;
  onCloseMobile?: () => void;
}) {
  const pathname = usePathname() || "";
  const router = useRouter();
  const [settingsMenuOpen, setSettingsMenuOpen] = useState(false);
  const [settingsMenuDismissed, setSettingsMenuDismissed] = useState(false);
  const onSettingsRoute = isSettingsRoute(pathname);
  const showSettingsMenu =
    !collapsed &&
    !settingsMenuDismissed &&
    (onSettingsRoute || settingsMenuOpen);

  return (
    <aside
      className={clsx(
        "flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-neutral-200/80 bg-koraku-panel transition-[width] duration-200 ease-out",
        // Layered “pill input” border: hairline edge + white halo gap + soft outer stroke + float shadow
        "shadow-[0_0_0_3px_rgb(255_255_255),0_0_0_4px_rgb(229_229_229_/_0.55),0_14px_40px_-14px_rgb(0_0_0_/_0.09)]",
        collapsed
          ? "w-[14rem] md:w-[3.75rem] p-3 md:px-1.5 md:py-2.5"
          : "w-[14rem] p-3",
      )}
    >
      <div
        className={clsx(
          "flex shrink-0 items-center",
          collapsed
            ? "mb-4 w-full flex-row justify-between gap-2 md:mb-1.5 md:flex-col md:gap-1.5"
            : "mb-4 w-full flex-row justify-between gap-2",
        )}
      >
        <div className="flex min-w-0 items-center gap-2.5">
          <BrandMark size={48} priority />
          <div
            className={clsx(
              "min-w-0 flex-1",
              collapsed ? "block md:hidden" : "block",
            )}
          >
            <p className="truncate text-[15px] font-semibold leading-tight text-neutral-900">
              Koraku
            </p>
          </div>
        </div>

        {/* Mobile close button */}
        {onCloseMobile && (
          <button
            type="button"
            onClick={onCloseMobile}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-neutral-500 transition hover:bg-white/90 hover:text-neutral-900 md:hidden"
            aria-label="Close sidebar"
            title="Close sidebar"
          >
            <X className="h-4 w-4" strokeWidth={iconStroke} />
          </button>
        )}

        <button
          type="button"
          onClick={onToggleCollapse}
          className={clsx(
            "h-9 w-9 shrink-0 items-center justify-center rounded-full text-neutral-500 transition hover:bg-white/90 hover:text-neutral-900",
            onCloseMobile ? "hidden md:flex" : "flex",
          )}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <PanelLeft className="h-4 w-4" strokeWidth={iconStroke} />
          ) : (
            <PanelLeftClose className="h-4 w-4" strokeWidth={iconStroke} />
          )}
        </button>
      </div>

      <nav className="flex shrink-0 flex-col gap-0.5">
        {nav.map((item) => {
          const Icon = item.icon;
          if (item.accent) {
            return (
              <button
                key={item.label}
                type="button"
                disabled={chatsLoading}
                onClick={onNewChat}
                className={clsx(
                  "flex items-center gap-2.5 rounded-2xl px-2.5 py-2 text-left text-[13px] font-semibold text-neutral-800 transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:bg-transparent",
                  collapsed
                    ? "justify-start px-2.5 md:justify-center md:px-0"
                    : "",
                )}
                aria-label="New chat"
                title="New chat"
              >
                <Icon
                  className="h-4 w-4 shrink-0 text-neutral-600"
                  strokeWidth={iconStroke}
                />
                <span className={clsx(collapsed ? "block md:hidden" : "block")}>
                  {item.label}
                </span>
              </button>
            );
          }
          if (!("href" in item)) return null;
          const { href } = item as { href: string };
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-2.5 rounded-2xl px-2.5 py-2 text-left text-[13px] font-semibold transition",
                collapsed && "justify-start px-2.5 md:justify-center md:px-0",
                active
                  ? "bg-white text-neutral-900 shadow-sm ring-1 ring-neutral-200/70"
                  : "text-neutral-600 hover:bg-white/80 hover:text-neutral-900",
              )}
              aria-label={item.label}
              title={item.label}
            >
              <Icon className="h-4 w-4 shrink-0" strokeWidth={iconStroke} />
              <span className={clsx(collapsed ? "block md:hidden" : "block")}>
                {item.label}
              </span>
            </Link>
          );
        })}
      </nav>

      {!collapsed || true ? (
        <div
          className={clsx(
            collapsed ? "block md:hidden" : "block",
            "min-h-0 flex-1 flex flex-col",
          )}
        >
          <SidebarChatList
            chatsLoading={chatsLoading}
            sessions={sessions}
            activeId={activeId}
            streamingSessionIds={streamingSessionIds}
            deletingSessionIds={deletingSessionIds}
            refreshingSessionIds={refreshingSessionIds}
            onSelectSession={onSelectSession}
            onDeleteChat={onDeleteChat}
            onRefreshChat={onRefreshChat}
          />
        </div>
      ) : null}

      <div className="mt-auto flex shrink-0 flex-col gap-2 border-t border-neutral-200/60 pt-2">
        {showSettingsMenu ? (
          <SidebarSettingsMenu
            onClose={() => {
              setSettingsMenuDismissed(true);
              setSettingsMenuOpen(false);
            }}
          />
        ) : (
          <button
            type="button"
            onClick={() => {
              const isMobile =
                typeof window !== "undefined" && window.innerWidth < 768;
              if (collapsed && !isMobile) {
                router.push(SETTINGS_PANEL_HREF.profile);
                return;
              }
              setSettingsMenuDismissed(false);
              setSettingsMenuOpen(true);
            }}
            aria-expanded={false}
            aria-label="Settings"
            title="Settings"
            className={clsx(
              "flex w-full shrink-0 items-center gap-2.5 rounded-2xl px-2.5 py-2 text-left text-[13px] font-semibold transition",
              !collapsed && onSettingsRoute
                ? "bg-white text-neutral-900 shadow-sm ring-1 ring-neutral-200/80"
                : "text-neutral-600 hover:bg-white/80 hover:text-neutral-900",
              collapsed && "justify-start px-2.5 md:justify-center md:px-0",
            )}
          >
            <Settings2 className="h-4 w-4 shrink-0" strokeWidth={iconStroke} />
            <span className={clsx(collapsed ? "block md:hidden" : "block")}>
              Settings
            </span>
          </button>
        )}
        <div
          className={clsx(
            "min-w-0",
            collapsed
              ? "flex justify-start px-0.5 pb-0.5 md:justify-center md:px-0 md:pb-0"
              : "w-full px-0.5 pb-0.5",
          )}
        >
          <AccountMenu collapsed={collapsed} />
        </div>
      </div>
    </aside>
  );
}
