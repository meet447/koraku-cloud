"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { LANDING_CONTAINER, LANDING_PAGE_BG, LANDING_PAGE_BG_BLUR, LANDING_SECTION } from "@/components/landing/landing-layout";
import { APP_BASE } from "@/lib/app-path";
import { createBrowserSupabaseClient } from "@/lib/supabase/browser";
import { cn } from "@/lib/cn";

export function TopNav() {
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);

  const supabase = useMemo(() => {
    try {
      return createBrowserSupabaseClient();
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    if (!supabase) {
      setLoggedIn(false);
      return;
    }

    let cancelled = false;
    void supabase.auth.getUser().then(({ data }) => {
      if (!cancelled) setLoggedIn(Boolean(data.user));
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(() => {
      void supabase.auth.getUser().then(({ data }) => {
        if (!cancelled) setLoggedIn(Boolean(data.user));
      });
    });

    return () => {
      cancelled = true;
      subscription.unsubscribe();
    };
  }, [supabase]);

  return (
    <header className={cn("sticky top-0 z-50 border-b border-black/10 backdrop-blur-xl", LANDING_PAGE_BG_BLUR)}>
      <nav className={`${LANDING_CONTAINER} flex h-[72px] items-center justify-between px-5 sm:px-8`}>
        <Link href="/" className="font-landing-serif text-2xl font-semibold tracking-[-0.04em] text-[#282522]">
          Koraku
        </Link>

        <div className="flex items-center gap-2">
          {loggedIn === null ? (
            <span className="h-9 w-24 animate-pulse rounded-full bg-stone-200" aria-hidden />
          ) : loggedIn || !supabase ? (
            <Link
              href={APP_BASE}
              className="rounded-full bg-[#171717] px-4 py-2 text-[13px] font-medium text-white shadow-[0_8px_18px_rgba(0,0,0,0.2)] transition hover:-translate-y-0.5"
            >
              Open app
            </Link>
          ) : (
            <Link
              href="/sign-in"
              className="rounded-full bg-[#171717] px-4 py-2 text-[13px] font-medium text-white shadow-[0_8px_18px_rgba(0,0,0,0.2)] transition hover:-translate-y-0.5"
            >
              Sign in
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}
