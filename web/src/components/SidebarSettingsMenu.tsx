"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { SlidersHorizontal } from "lucide-react";
import { SETTINGS_MENU_ITEMS } from "@/lib/settings-panel";

const iconStroke = 1.5;

export function SidebarSettingsMenu({ onClose }: { onClose?: () => void }) {
  const pathname = usePathname() || "";

  return (
    <div
      className="shrink-0"
      role="region"
      aria-label="Settings menu"
    >
      <div className="rounded-[18px] bg-white px-1.5 py-1.5 shadow-sm ring-1 ring-neutral-200/60">
        <button
          type="button"
          onClick={() => onClose?.()}
          aria-expanded
          className="flex w-full items-center gap-2 rounded-xl px-1.5 py-1.5 text-left transition hover:bg-neutral-50"
        >
          <SlidersHorizontal
            className="h-3.5 w-3.5 shrink-0 text-neutral-500"
            strokeWidth={iconStroke}
            aria-hidden
          />
          <span className="text-[13px] font-bold text-koraku-ink">Settings</span>
        </button>

        <ul className="mt-0.5 space-y-0.5">
          {SETTINGS_MENU_ITEMS.map(({ id, label, icon: Icon, href }) => {
            const active = pathname === href;
            return (
              <li key={id}>
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={clsx(
                    "flex w-full items-center gap-2.5 rounded-xl px-2 py-2 text-left text-[13px] font-semibold transition",
                    active
                      ? "bg-neutral-100 text-koraku-ink"
                      : "text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900",
                  )}
                >
                  <Icon
                    className="h-4 w-4 shrink-0 text-neutral-400"
                    strokeWidth={iconStroke}
                    aria-hidden
                  />
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
