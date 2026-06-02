import Link from "next/link";
import type { ReactNode } from "react";
import { BrandMark } from "@/components/BrandMark";
import { landingFontClassName } from "@/components/landing/LandingShell";
import {
  LANDING_CONTAINER,
  LANDING_PAGE_BG,
  LANDING_PAGE_BG_BLUR,
} from "@/components/landing/landing-layout";
import { cn } from "@/lib/cn";

export function AuthPageLayout({ children }: { children: ReactNode }) {
  return (
    <div
      className={cn(
        landingFontClassName(),
        LANDING_PAGE_BG,
        "min-h-dvh text-[#282522] lg:grid lg:grid-cols-[240px_1fr]",
      )}
    >
      <aside className={cn("hidden h-dvh flex-col border-r border-black/10 px-7 py-8 lg:flex", LANDING_PAGE_BG)}>
        <Link href="/" className="inline-flex items-center" aria-label="Koraku home">
          <BrandMark size={96} priority />
        </Link>
        <div className="flex flex-1 flex-col justify-center">
          <p className="landing-pixel-headline text-[2.4rem] font-semibold leading-[0.92] tracking-[-0.06em] text-[#282522]">
            Your agents,
            <br />
            <span className="text-stone-400">your workflow</span>
          </p>
          <p className="mt-5 max-w-[200px] text-sm leading-6 text-stone-500">
            Connect tools, route models, and run work from one place.
          </p>
        </div>
      </aside>

      <main className="flex min-h-dvh flex-col">
        <header className={cn("border-b border-black/10 backdrop-blur-xl", LANDING_PAGE_BG_BLUR)}>
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

        <div className="flex flex-1 items-center justify-center px-5 py-12 sm:px-8">
          <div className="w-full max-w-[440px]">{children}</div>
        </div>
      </main>
    </div>
  );
}
