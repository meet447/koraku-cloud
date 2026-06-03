"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { BrandMark } from "@/components/BrandMark";
import { navItems } from "@/components/landing/landing-data";
import { LANDING_PAGE_BG } from "@/components/landing/landing-layout";
import { cn } from "@/lib/cn";

const SCROLL_ROOT_SELECTOR = "[data-landing-scroll]";
const ACTIVE_OFFSET_PX = 140;

function sectionIdFromHref(href: string): string {
  return href.startsWith("#") ? href.slice(1) : href;
}

export function LeftRail() {
  const sectionIds = useMemo(
    () => navItems.map((item) => sectionIdFromHref(item.href)),
    [],
  );
  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    const root = document.querySelector<HTMLElement>(SCROLL_ROOT_SELECTOR);
    if (!root) return;

    const updateActive = () => {
      const sections = sectionIds
        .map((id) => document.getElementById(id))
        .filter((el): el is HTMLElement => el != null);

      if (!sections.length) return;

      const rootTop = root.getBoundingClientRect().top;
      let current: string | null = null;

      for (const section of sections) {
        const top = section.getBoundingClientRect().top - rootTop;
        if (top <= ACTIVE_OFFSET_PX) {
          current = section.id;
        }
      }

      setActiveId(current);
    };

    updateActive();
    root.addEventListener("scroll", updateActive, { passive: true });
    window.addEventListener("resize", updateActive);

    return () => {
      root.removeEventListener("scroll", updateActive);
      window.removeEventListener("resize", updateActive);
    };
  }, [sectionIds]);

  return (
    <aside className={cn("hidden h-screen overflow-hidden border-r border-black/10 px-7 py-8 lg:flex lg:flex-col", LANDING_PAGE_BG)}>
      <Link href="/" className="inline-flex items-center">
        <BrandMark size={96} priority />
      </Link>

      <nav className="flex flex-1 flex-col justify-center" aria-label="Page sections">
        <div className="grid gap-3">
          {navItems.map((item) => {
            const id = sectionIdFromHref(item.href);
            const isActive = activeId === id;

            return (
              <a
                key={item.label}
                href={item.href}
                aria-current={isActive ? "location" : undefined}
                className={cn(
                  "rounded-md px-3 py-2 text-lg font-semibold tracking-[-0.02em] transition",
                  isActive
                    ? "bg-white text-stone-900 shadow-[4px_4px_0_rgba(0,0,0,0.04)] ring-1 ring-black/10"
                    : "text-stone-400 hover:text-stone-900",
                )}
              >
                {item.label}
              </a>
            );
          })}
        </div>
      </nav>
    </aside>
  );
}
