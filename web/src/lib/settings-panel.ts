import type { LucideIcon } from "lucide-react";
import { Bot, Shield, UserRound } from "lucide-react";
import { APP_BASE } from "@/lib/app-path";

export const SETTINGS_PANELS = ["profile", "agent", "account"] as const;

export type SettingsPanel = (typeof SETTINGS_PANELS)[number];

export const SETTINGS_PANEL_LABELS: Record<SettingsPanel, string> = {
  profile: "Personal info",
  agent: "Agent info",
  account: "Account & data",
};

export const SETTINGS_PANEL_HREF: Record<SettingsPanel, string> = {
  profile: `${APP_BASE}/settings/profile`,
  agent: `${APP_BASE}/settings/agent`,
  account: `${APP_BASE}/settings/account`,
};

export const SETTINGS_MENU_ITEMS: {
  id: SettingsPanel;
  label: string;
  icon: LucideIcon;
  href: string;
}[] = [
  {
    id: "profile",
    label: SETTINGS_PANEL_LABELS.profile,
    icon: UserRound,
    href: SETTINGS_PANEL_HREF.profile,
  },
  {
    id: "agent",
    label: SETTINGS_PANEL_LABELS.agent,
    icon: Bot,
    href: SETTINGS_PANEL_HREF.agent,
  },
  {
    id: "account",
    label: SETTINGS_PANEL_LABELS.account,
    icon: Shield,
    href: SETTINGS_PANEL_HREF.account,
  },
];

export function parseSettingsPanel(value: string | null): SettingsPanel | null {
  if (value && (SETTINGS_PANELS as readonly string[]).includes(value)) {
    return value as SettingsPanel;
  }
  return null;
}

export function settingsPanelFromPathname(pathname: string): SettingsPanel | null {
  for (const id of SETTINGS_PANELS) {
    if (pathname === SETTINGS_PANEL_HREF[id]) return id;
  }
  return null;
}

export function isSettingsRoute(pathname: string): boolean {
  return pathname === `${APP_BASE}/settings` || pathname.startsWith(`${APP_BASE}/settings/`);
}
