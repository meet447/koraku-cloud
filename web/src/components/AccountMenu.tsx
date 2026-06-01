"use client";

import type { User } from "@supabase/supabase-js";
import { LogIn, LogOut, User as UserIcon, UserPlus } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { createBrowserSupabaseClient } from "@/lib/supabase/browser";

const iconStroke = 1.5;

export function AccountMenu({ collapsed = false }: { collapsed?: boolean }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null | undefined>(undefined);

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
    void supabase.auth.getUser().then(({ data }) => {
      if (!cancelled) setUser(data.user ?? null);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => {
      cancelled = true;
      subscription.unsubscribe();
    };
  }, [supabase]);

  if (user === undefined) {
    return (
      <span
        className={collapsed ? "flex justify-center text-xs text-neutral-400" : "text-xs text-neutral-400"}
        aria-live="polite"
      >
        …
      </span>
    );
  }

  if (!supabase || !user) {
    if (collapsed) {
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

  const label =
    (user.user_metadata?.full_name as string | undefined)?.trim() ||
    user.user_metadata?.name ||
    user.email;

  const signOut = () => {
    void (async () => {
      await supabase.auth.signOut();
      if (pathname.startsWith("/app")) {
        router.replace("/");
      } else {
        router.refresh();
      }
    })();
  };

  if (collapsed) {
    return (
      <div
        className="flex flex-col items-center gap-1.5 py-0.5"
        title={typeof label === "string" ? label : user.email ?? undefined}
      >
        <UserIcon className="h-4 w-4 shrink-0 text-neutral-600" strokeWidth={iconStroke} aria-hidden />
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
    <div className="flex w-full min-w-0 flex-col gap-2">
      <span
        className="truncate text-[13px] font-medium text-neutral-800"
        title={user.email ?? undefined}
      >
        {label}
      </span>
      <button
        type="button"
        className="w-full shrink-0 rounded-2xl border border-neutral-200 px-2.5 py-2 text-left text-[13px] font-semibold text-neutral-700 transition hover:bg-white/80"
        onClick={signOut}
      >
        Sign out
      </button>
    </div>
  );
}
