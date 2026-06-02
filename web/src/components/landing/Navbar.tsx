"use client";

import Link from "next/link";
import { ArrowUpRight, ChevronRight } from "lucide-react";
import { motion } from "motion/react";
import { BrandMark } from "@/components/BrandMark";
import { APP_BASE } from "@/lib/app-path";
import { landingText } from "@/lib/landing-theme";

const NAV_ITEMS = [
  { label: "Memory", href: `${APP_BASE}/memory` },
  { label: "Connections", href: `${APP_BASE}/connections` },
  { label: "Automations", href: `${APP_BASE}/automations`, hasDropdown: true },
  { label: "Trust", href: "/privacy", hasDropdown: true },
] as const;

export function Navbar() {
  return (
    <nav className="relative z-10 flex w-full items-center justify-between px-6 py-6 md:px-10">
      <div className="hidden flex-1 md:block" />

      <ul className={`hidden items-center gap-8 text-sm font-normal md:flex ${landingText.nav}`}>
        {NAV_ITEMS.map((item) => (
          <li key={item.label}>
            <Link
              href={item.href}
              className="group flex cursor-pointer items-center gap-1 transition-opacity hover:opacity-70"
            >
              {item.label}
              {"hasDropdown" in item && item.hasDropdown ? (
                <ChevronRight
                  className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
                  aria-hidden
                />
              ) : null}
            </Link>
          </li>
        ))}
      </ul>

      <div className="flex items-center gap-3 md:hidden">
        <BrandMark size={36} priority />
        <span className={`text-xl font-normal tracking-tighter ${landingText.headline}`}>Koraku</span>
      </div>

      <div className="flex flex-1 justify-end">
        <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
          <Link
            href={APP_BASE}
            className="group flex items-center gap-2 rounded-full bg-[#1c1917] py-1.5 pl-2 pr-4 text-white transition-colors hover:bg-[#292524] md:gap-3 md:py-2 md:pr-6"
          >
            <div className="flex items-center justify-center rounded-full bg-white/15 p-1 md:p-1.5">
              <ArrowUpRight className="h-4 w-4 text-white md:h-5 md:w-5" aria-hidden />
            </div>
            <span className="text-xs font-normal md:text-sm">Open app</span>
          </Link>
        </motion.div>
      </div>
    </nav>
  );
}
