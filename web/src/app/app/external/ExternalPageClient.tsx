"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Loader2, MessageCircle, Phone } from "lucide-react";
import { APP_BASE } from "@/lib/app-path";
import { KORAKU_COPY } from "@/lib/korakuBrand";
import { errorMessage } from "@/lib/error-message";
import { korakuFetchJson } from "@/lib/koraku-fetch";
import { korakuUi } from "@/lib/koraku-ui";
import { SettingsPageShell } from "@/components/SettingsPageShell";
import { KorakuAlert } from "@/components/KorakuAlert";
import { KorakuButton } from "@/components/KorakuButton";
import { KorakuMessageQr } from "@/components/KorakuMessageQr";
import { useKorakuChatShell } from "@/context/KorakuChatContext";
import { messagesAppUrl } from "@/lib/messages-app-url";

type ExternalStatus = {
  configured: boolean;
  from_number: string | null;
  linked: boolean;
  phone_e164: string | null;
  imessage_thread_id: string | null;
};

export function ExternalPageClient() {
  const shell = useKorakuChatShell();
  const [status, setStatus] = useState<ExternalStatus | null>(null);
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [showLinkForm, setShowLinkForm] = useState(false);

  const load = useCallback(async () => {
    try {
      setStatus(await korakuFetchJson<ExternalStatus>("/api/external/status"));
    } catch {
      /* ignore — page shows loading until status resolves */
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function startVerify() {
    setError(null);
    setBusy(true);
    try {
      const j = await korakuFetchJson<{ detail?: string; sent?: boolean }>(
        "/koraku-api/sendblue/verify/start",
        { method: "POST", json: { phone: phone.trim() } },
      );
      setSent(Boolean(j.sent));
    } catch (e) {
      setError(errorMessage(e, "Could not send verification code"));
    } finally {
      setBusy(false);
    }
  }

  async function confirmVerify() {
    setError(null);
    setBusy(true);
    try {
      const j = await korakuFetchJson<{
        detail?: string;
        imessage_thread_id?: string;
      }>("/koraku-api/sendblue/verify/confirm", {
        method: "POST",
        json: { phone: phone.trim(), code: code.trim() },
      });
      await Promise.all([load(), shell.reloadSessions()]);
      if (j.imessage_thread_id) {
        shell.selectSession(j.imessage_thread_id);
      }
    } catch (e) {
      setError(errorMessage(e, "Invalid code"));
    } finally {
      setBusy(false);
    }
  }

  if (!status) {
    return (
      <SettingsPageShell
        eyebrow="External"
        title="Message from your phone"
        description={KORAKU_COPY.externalIntro}
      >
        <div className="flex justify-center py-12">
          <Loader2 className="h-7 w-7 animate-spin text-koraku-muted" aria-label="Loading" />
        </div>
      </SettingsPageShell>
    );
  }

  return (
    <SettingsPageShell
      eyebrow="External"
      title="Message from your phone"
      description={KORAKU_COPY.externalIntro}
      action={
        <KorakuButton variant="secondary" size="sm" onClick={() => void load()} disabled={busy}>
          Refresh
        </KorakuButton>
      }
    >
      {error ? <KorakuAlert variant="error">{error}</KorakuAlert> : null}

      {!status.configured ? (
        <KorakuAlert variant="warning">{KORAKU_COPY.externalNotConfigured}</KorakuAlert>
      ) : null}

      {status.configured && status.from_number ? (
        <section className={korakuUi.panel}>
          <div className="mb-3 flex items-center gap-2">
            <Phone className="h-4 w-4 text-orange-700" aria-hidden />
            <h2 className="text-base font-bold text-koraku-ink">Koraku number</h2>
          </div>
          <div className={korakuUi.card}>
            <div className="flex flex-col items-center text-center">
              <p className="max-w-md text-xs font-medium text-koraku-muted">
                Text or send voice notes from iMessage or SMS. Tap the number or scan the QR.
              </p>
              <a
                href={messagesAppUrl(status.from_number)}
                className="mt-4 text-3xl font-bold tracking-tight tabular-nums text-orange-700 underline-offset-4 hover:underline sm:text-4xl"
              >
                {status.from_number}
              </a>
              <KorakuMessageQr
                phoneE164={status.from_number}
                size={140}
                className="mt-5"
              />
            </div>
          </div>
        </section>
      ) : null}

      {status.linked ? (
        <section className={korakuUi.panel}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex min-w-0 items-start gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-50 ring-1 ring-emerald-200/70">
                <CheckCircle2 className="h-4 w-4 text-emerald-700" aria-hidden />
              </div>
              <div className="min-w-0">
                <h2 className="text-base font-bold text-koraku-ink">Phone linked</h2>
                <p className="mt-1 text-xs font-medium leading-relaxed text-koraku-muted">
                  {KORAKU_COPY.externalLinkedHint}
                </p>
              </div>
            </div>
            <Link
              href={APP_BASE}
              onClick={() => {
                if (status.imessage_thread_id) {
                  shell.selectSession(status.imessage_thread_id);
                }
              }}
            >
              <KorakuButton size="sm">Open thread</KorakuButton>
            </Link>
          </div>
        </section>
      ) : status.configured ? (
        <section className={korakuUi.panel}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <MessageCircle className="h-4 w-4 text-koraku-ink" aria-hidden />
              <h2 className="text-base font-bold text-koraku-ink">Link your phone</h2>
            </div>
            {!showLinkForm ? (
              <KorakuButton
                variant="secondary"
                size="sm"
                onClick={() => setShowLinkForm(true)}
              >
                Verify number
              </KorakuButton>
            ) : null}
          </div>
          <p className="mt-2 text-xs font-medium leading-relaxed text-koraku-muted">
            After you message the Koraku number, verify here so threads sync to the web app.
            Your number stays private on this page.
          </p>

          {showLinkForm ? (
            <div className={`mt-3 ${korakuUi.card}`}>
              <div className="space-y-3">
                <div>
                  <label className={korakuUi.fieldLabel} htmlFor="external-phone">
                    Phone to verify
                  </label>
                  <input
                    id="external-phone"
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className={`mt-2 ${korakuUi.input}`}
                    placeholder="+1…"
                    disabled={busy}
                    autoComplete="tel"
                  />
                </div>

                <KorakuButton
                  fullWidth
                  size="sm"
                  disabled={busy || !phone.trim()}
                  onClick={() => void startVerify()}
                >
                  {busy ? "Sending…" : "Send verification code"}
                </KorakuButton>

                {sent ? (
                  <p className="text-xs font-medium leading-relaxed text-koraku-muted">
                    Check iMessage or SMS for your code, or reply{" "}
                    <code className="rounded bg-koraku-panel px-1 py-0.5 font-mono text-[11px] ring-1 ring-neutral-200/80">
                      KORAKU-######
                    </code>{" "}
                    to the Koraku number above.
                  </p>
                ) : null}

                <div className="border-t border-neutral-200/80 pt-3">
                  <label className={korakuUi.fieldLabel} htmlFor="external-code">
                    Verification code
                  </label>
                  <input
                    id="external-code"
                    type="text"
                    inputMode="numeric"
                    maxLength={12}
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    className={`mt-2 ${korakuUi.input}`}
                    placeholder="6 digits"
                    disabled={busy}
                  />
                  <KorakuButton
                    variant="secondary"
                    fullWidth
                    size="sm"
                    disabled={busy || !phone.trim() || !code.trim()}
                    onClick={() => void confirmVerify()}
                    className="mt-3"
                  >
                    Confirm and link
                  </KorakuButton>
                </div>
              </div>
            </div>
          ) : null}
        </section>
      ) : null}
    </SettingsPageShell>
  );
}
