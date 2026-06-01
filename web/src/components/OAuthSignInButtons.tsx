"use client";

import { useMemo, useState } from "react";
import { createBrowserSupabaseClient } from "@/lib/supabase/browser";
import { readPostAuthRedirect } from "@/lib/auth-redirect";

type Provider = "google" | "github";

const btn =
  "flex w-full items-center justify-center gap-2 rounded-lg border border-neutral-200 bg-white px-4 py-2.5 text-sm font-medium text-neutral-800 shadow-sm hover:bg-neutral-50 disabled:opacity-50";

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
      <p className="text-sm text-amber-800" role="alert">
        Supabase is not configured. Set NEXT_PUBLIC_SUPABASE_URL and
        NEXT_PUBLIC_SUPABASE_ANON_KEY in web/.env.local, then enable Google and/or
        GitHub under Authentication → Providers in the Supabase dashboard.
      </p>
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
      {error ? (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}
      <button
        type="button"
        className={btn}
        disabled={loading !== null}
        onClick={() => void startOAuth("google")}
      >
        {loading === "google" ? "Redirecting…" : "Continue with Google"}
      </button>
      <button
        type="button"
        className={btn}
        disabled={loading !== null}
        onClick={() => void startOAuth("github")}
      >
        {loading === "github" ? "Redirecting…" : "Continue with GitHub"}
      </button>
    </div>
  );
}
