"use client";

import { useMemo, useState } from "react";
import { createBrowserSupabaseClient } from "@/lib/supabase/browser";
import { readPostAuthRedirect } from "@/lib/auth-redirect";
import { KORAKU_COPY } from "@/lib/korakuBrand";
import { KorakuAlert } from "@/components/KorakuAlert";
import { KorakuButton } from "@/components/KorakuButton";

type Provider = "google" | "github";

const btn = "rounded-xl";

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
      {error ? (
        <KorakuAlert variant="error">{error}</KorakuAlert>
      ) : null}
      <KorakuButton
        variant="secondary"
        fullWidth
        className={btn}
        disabled={loading !== null}
        onClick={() => void startOAuth("google")}
      >
        {loading === "google" ? "Redirecting…" : "Continue with Google"}
      </KorakuButton>
      <KorakuButton
        variant="secondary"
        fullWidth
        className={btn}
        disabled={loading !== null}
        onClick={() => void startOAuth("github")}
      >
        {loading === "github" ? "Redirecting…" : "Continue with GitHub"}
      </KorakuButton>
    </div>
  );
}
