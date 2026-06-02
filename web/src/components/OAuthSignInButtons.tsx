"use client";

import { useMemo, useState } from "react";
import { KorakuAlert } from "@/components/KorakuAlert";
import { LANDING_SURFACE } from "@/components/landing/landing-layout";
import { readPostAuthRedirect } from "@/lib/auth-redirect";
import { KORAKU_COPY } from "@/lib/korakuBrand";
import { cn } from "@/lib/cn";
import { createBrowserSupabaseClient } from "@/lib/supabase/browser";

type Provider = "google" | "github";

const PROVIDERS: { id: Provider; label: string; icon: string }[] = [
  { id: "google", label: "Continue with Google", icon: "https://cdn.simpleicons.org/google/4285F4" },
  { id: "github", label: "Continue with GitHub", icon: "https://cdn.simpleicons.org/github/181717" },
];

export function OAuthSignInButtons() {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<Provider | null>(null);

  const supabase = useMemo(() => {
    try {
      return createBrowserSupabaseClient();
    } catch {
      return null;
    }
  }, []);

  if (!supabase) {
    return (
      <KorakuAlert variant="warning" role="alert">
        {KORAKU_COPY.authNotConfigured}
      </KorakuAlert>
    );
  }

  async function startOAuth(provider: Provider) {
    if (!supabase) return;
    setError(null);
    setLoading(provider);
    try {
      const origin = window.location.origin;
      const next = readPostAuthRedirect();
      const redirectTo = `${origin}/auth/callback?next=${encodeURIComponent(next)}`;
      const { data, error: err } = await supabase.auth.signInWithOAuth({
        provider,
        options: { redirectTo },
      });
      if (err) {
        setError(err.message || "Could not start sign-in");
        setLoading(null);
        return;
      }
      const url = data?.url;
      if (typeof url === "string" && url.length > 0) {
        window.location.assign(url);
        return;
      }
      setError("Unexpected response from the auth server.");
    } catch (ex) {
      setError(String((ex as Error)?.message || ex));
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {error ? <KorakuAlert variant="error">{error}</KorakuAlert> : null}
      {PROVIDERS.map((provider) => (
        <button
          key={provider.id}
          type="button"
          disabled={loading !== null}
          onClick={() => void startOAuth(provider.id)}
          className={cn(
            "flex h-12 w-full items-center justify-center gap-3 rounded-md border border-black/10 text-sm font-semibold text-stone-900 shadow-[4px_4px_0_rgba(0,0,0,0.04)] transition",
            LANDING_SURFACE,
            "hover:border-black/20 hover:bg-white disabled:cursor-not-allowed disabled:opacity-50",
          )}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={provider.icon} alt="" width={18} height={18} className="h-[18px] w-[18px] object-contain" />
          {loading === provider.id ? "Redirecting…" : provider.label}
        </button>
      ))}
    </div>
  );
}
