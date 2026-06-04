import type { LucideIcon } from "lucide-react";
import { BarChart3, Bot, Shield, UserRound } from "lucide-react";
import { APP_BASE } from "@/lib/app-path";

const SETTINGS_PANELS = ["profile", "agent", "account", "usage"] as const;

type SettingsPanel = (typeof SETTINGS_PANELS)[number];

const SETTINGS_PANEL_LABELS: Record<SettingsPanel, string> = {
  profile: "Personal info",
  agent: "Agent info",
  account: "Account & data",
  usage: "Usage",
};

export const SETTINGS_PANEL_HREF: Record<SettingsPanel, string> = {
  profile: `${APP_BASE}/settings/profile`,
  agent: `${APP_BASE}/settings/agent`,
  account: `${APP_BASE}/settings/account`,
  usage: `${APP_BASE}/settings/usage`,
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
  {
    id: "usage",
    label: SETTINGS_PANEL_LABELS.usage,
    icon: BarChart3,
    href: SETTINGS_PANEL_HREF.usage,
  },
];

export function isSettingsRoute(pathname: string): boolean {
  return pathname === `${APP_BASE}/settings` || pathname.startsWith(`${APP_BASE}/settings/`);
}
