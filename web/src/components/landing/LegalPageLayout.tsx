import Link from "next/link";
import type { ReactNode } from "react";
import { BrandMark } from "@/components/BrandMark";
import { landingFontClassName } from "@/components/landing/LandingShell";
import {
  LANDING_CONTAINER,
  LANDING_PAGE_BG,
  LANDING_PAGE_BG_BLUR,
  LANDING_SECTION,
} from "@/components/landing/landing-layout";
import { legalPages, type LegalPageSlug } from "@/lib/legal-pages";
import { cn } from "@/lib/cn";

export function LegalPageLayout({
  children,
  activeSlug,
}: {
  children: ReactNode;
  activeSlug?: LegalPageSlug;
}) {
  return (
    <div
      className={cn(
        landingFontClassName(),
        LANDING_PAGE_BG,
        "h-dvh overflow-hidden text-[#282522] lg:grid lg:grid-cols-[240px_1fr]",
      )}
    >
      <aside
        className={cn(
          "hidden h-dvh shrink-0 flex-col overflow-hidden border-r border-black/10 px-7 py-8 lg:flex",
          LANDING_PAGE_BG,
        )}
      >
        <Link href="/" className="inline-flex items-center" aria-label="Koraku home">
          <BrandMark size={96} priority />
        </Link>
        <nav className="mt-10 flex flex-1 flex-col gap-1" aria-label="Legal pages">
          {legalPages.map((page) => {
            const isActive = activeSlug === page.slug;
            return (
              <Link
                key={page.slug}
                href={page.href}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "rounded-md px-3 py-2 text-[15px] font-semibold transition",
                  isActive
                    ? "bg-white text-stone-900 shadow-[4px_4px_0_rgba(0,0,0,0.04)] ring-1 ring-black/10"
                    : "text-stone-400 hover:bg-white hover:text-stone-900 hover:shadow-sm hover:ring-1 hover:ring-black/10",
                )}
              >
                {page.label}
              </Link>
            );
          })}
        </nav>
        <Link href="/" className="text-sm font-medium text-stone-500 transition hover:text-stone-900">
          ← Back to home
        </Link>
      </aside>

      <div className="flex h-dvh min-w-0 flex-col overflow-y-auto overflow-x-hidden">
        <header className={cn("sticky top-0 z-50 shrink-0 border-b border-black/10 backdrop-blur-xl", LANDING_PAGE_BG_BLUR)}>
          <nav
            className={`${LANDING_CONTAINER} flex h-[72px] items-center justify-between px-5 sm:px-8`}
          >
            <Link
              href="/"
              className="font-landing-serif text-2xl font-semibold tracking-[-0.04em] text-[#282522] lg:hidden"
            >
              Koraku
            </Link>
            <Link
              href="/"
              className="text-sm font-medium text-stone-500 transition hover:text-stone-900 lg:ml-auto"
            >
              ← Back to home
            </Link>
          </nav>
        </header>

        <main className={`flex-1 ${LANDING_SECTION}`}>
          <div className={`${LANDING_CONTAINER} max-w-3xl pb-20`}>{children}</div>
        </main>

        <footer className="shrink-0 border-t border-black/10 bg-[#fafafa] px-5 py-8 sm:px-8">
          <div className={`${LANDING_CONTAINER} flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between`}>
            <p className="text-xs text-stone-400">Koraku © 2026</p>
            <div className="flex flex-wrap gap-x-5 gap-y-2">
              {legalPages.map((page) => (
                <Link
                  key={page.slug}
                  href={page.href}
                  className="text-xs font-medium text-stone-500 transition hover:text-stone-800"
                >
                  {page.label}
                </Link>
              ))}
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
