"use client";

import type { User } from "@supabase/supabase-js";
import { LogIn, LogOut, UserPlus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { UserAvatar } from "@/components/UserAvatar";
import { clearOnboardingClientState } from "@/lib/onboarding";
import { createBrowserSupabaseClient } from "@/lib/supabase/browser";
import { getUserDisplayName } from "@/lib/user-profile";

const iconStroke = 1.5;

export function AccountMenu({ collapsed = false }: { collapsed?: boolean }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const actuallyCollapsed = collapsed && !isMobile;

  const supabase = useMemo(() => {
    try {
      return createBrowserSupabaseClient();
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    if (!supabase) {
      setUser(null);
      return;
    }

    let cancelled = false;
    const applyUser = (next: User | null) => {
      if (!cancelled) setUser(next);
    };

    void supabase.auth.getUser().then(({ data }) => {
      applyUser(data.user ?? null);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(() => {
      void supabase.auth.getUser().then(({ data }) => {
        applyUser(data.user ?? null);
      });
    });

    return () => {
      cancelled = true;
      subscription.unsubscribe();
    };
  }, [supabase]);

  if (user === undefined) {
    return (
      <span
        className={
          actuallyCollapsed ? "flex justify-center text-xs text-neutral-400" : "text-xs text-neutral-400"
        }
        aria-live="polite"
      >
        …
      </span>
    );
  }

  if (!supabase || !user) {
    if (actuallyCollapsed) {
      return (
        <div className="flex flex-col items-center gap-1">
          <Link
            href="/sign-in"
            title="Sign in"
            className="flex h-8 w-8 items-center justify-center rounded-xl text-neutral-600 transition hover:bg-white/80 hover:text-neutral-900"
          >
            <LogIn className="h-4 w-4" strokeWidth={iconStroke} aria-hidden />
            <span className="sr-only">Sign in</span>
          </Link>
          <Link
            href="/sign-up"
            title="Sign up"
            className="flex h-8 w-8 items-center justify-center rounded-xl text-neutral-600 transition hover:bg-white/80 hover:text-neutral-900"
          >
            <UserPlus className="h-4 w-4" strokeWidth={iconStroke} aria-hidden />
            <span className="sr-only">Sign up</span>
          </Link>
        </div>
      );
    }
    return (
      <div className="flex flex-col gap-2">
        <Link
          href="/sign-in"
          className="w-full rounded-2xl border border-neutral-200 px-2.5 py-2 text-center text-[13px] font-semibold text-koraku-ink transition hover:bg-white/80"
        >
          Sign in
        </Link>
        <Link
          href="/sign-up"
          className="w-full rounded-2xl bg-koraku-ink px-2.5 py-2 text-center text-[13px] font-semibold text-white transition hover:opacity-90"
        >
          Sign up
        </Link>
      </div>
    );
  }

  const label = getUserDisplayName(user);

  const signOut = () => {
    void (async () => {
      clearOnboardingClientState();
      await supabase.auth.signOut();
      if (window.location.pathname.startsWith("/app")) {
        router.replace("/");
      } else {
        router.refresh();
      }
    })();
  };

  if (actuallyCollapsed) {
    return (
      <div
        className="flex flex-col items-center gap-1.5 py-0.5"
        title={label}
      >
        <UserAvatar user={user} size={32} />
        <button
          type="button"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-neutral-200 text-neutral-700 transition hover:bg-white/80"
          onClick={signOut}
          aria-label="Sign out"
        >
          <LogOut className="h-3.5 w-3.5" strokeWidth={iconStroke} aria-hidden />
        </button>
      </div>
    );
  }

  return (
    <div className="flex w-full min-w-0 items-center gap-2 rounded-2xl bg-white/60 px-1 py-1 ring-1 ring-neutral-200/50">
      <UserAvatar user={user} size={32} />
      <span
        className="min-w-0 flex-1 truncate text-[13px] font-medium text-neutral-800"
        title={user.email ?? undefined}
      >
        {label}
      </span>
      <button
        type="button"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-neutral-200 text-neutral-600 transition hover:bg-white hover:text-neutral-900"
        onClick={signOut}
        aria-label="Sign out"
        title="Sign out"
      >
        <LogOut className="h-3.5 w-3.5" strokeWidth={iconStroke} aria-hidden />
      </button>
    </div>
  );
}
