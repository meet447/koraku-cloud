"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Loader2, MessageCircle, Phone } from "lucide-react";
import { APP_BASE } from "@/lib/app-path";
import { KORAKU_COPY } from "@/lib/korakuBrand";
import { errorMessage } from "@/lib/error-message";
import { korakuFetchJson } from "@/lib/koraku-fetch";
import { korakuUi } from "@/lib/koraku-ui";
import { KorakuAppPage } from "@/components/KorakuAppPage";
import { KorakuPageHeader } from "@/components/KorakuPageHeader";
import { KorakuAlert } from "@/components/KorakuAlert";
import { KorakuButton, korakuButtonClass } from "@/components/KorakuButton";
import { useKorakuChatShell } from "@/context/KorakuChatContext";

type ExternalStatus = {
  configured: boolean;
  from_number: string | null;
  linked: boolean;
  phone_e164: string | null;
  imessage_thread_id: string | null;
};

export default function ExternalPage() {
  const shell = useKorakuChatShell();
  const [status, setStatus] = useState<ExternalStatus | null>(null);
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

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
      await load();
      await shell.reloadSessions();
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
      <KorakuAppPage maxWidth="2xl" className="flex items-center justify-center">
        <Loader2 className="h-7 w-7 animate-spin text-koraku-muted" aria-label="Loading" />
      </KorakuAppPage>
    );
  }

  return (
    <KorakuAppPage maxWidth="2xl">
        <KorakuPageHeader
          eyebrow="External"
          title="Message Koraku from your phone"
          description={KORAKU_COPY.externalIntro}
        />

        {error ? (
          <KorakuAlert variant="error" className="mt-6">
            {error}
          </KorakuAlert>
        ) : null}

        <div className="mt-8 space-y-5">
          {!status.configured ? (
            <section
              className="rounded-[28px] border border-amber-200/80 bg-amber-50/90 px-5 py-4 ring-1 ring-amber-200/60"
              role="status"
            >
              <p className="text-sm font-medium leading-relaxed text-amber-950">
                {KORAKU_COPY.externalNotConfigured}
              </p>
            </section>
          ) : null}

          {status.from_number ? (
            <section className={korakuUi.card}>
              <div className="flex items-start gap-4">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-orange-50 ring-1 ring-orange-200/70">
                  <Phone className="h-5 w-5 text-orange-700" strokeWidth={2} aria-hidden />
                </div>
                <div className="min-w-0">
                  <h2 className="text-lg font-bold tracking-tight text-koraku-ink">
                    Koraku number
                  </h2>
                  <p className="mt-1 text-sm font-medium text-koraku-muted">
                    Save this contact to text Koraku from iMessage or SMS.
                  </p>
                  <a
                    href={`sms:${encodeURIComponent(status.from_number)}`}
                    className="mt-3 inline-block text-[15px] font-semibold text-orange-700 underline-offset-2 hover:underline"
                  >
                    {status.from_number}
                  </a>
                </div>
              </div>
            </section>
          ) : null}

          {status.linked ? (
            <section className="rounded-[28px] border border-emerald-200/80 bg-emerald-50/80 p-6 ring-1 ring-emerald-200/60">
              <div className="flex items-center gap-2 text-emerald-900">
                <CheckCircle2 className="h-5 w-5 shrink-0" aria-hidden />
                <h2 className="text-lg font-bold tracking-tight">Phone linked</h2>
              </div>
              <p className="mt-2 text-sm font-medium text-emerald-900/90">{status.phone_e164}</p>
              <p className="mt-2 text-sm font-medium text-emerald-800/90">
                {KORAKU_COPY.externalLinkedHint}
              </p>
              <Link
                href={APP_BASE}
                onClick={() => {
                  if (status.imessage_thread_id) {
                    shell.selectSession(status.imessage_thread_id);
                  }
                }}
                className={korakuButtonClass({ className: "mt-4" })}
              >
                Open message thread
              </Link>
            </section>
          ) : (
            <section className={korakuUi.card}>
              <div className="mb-5 flex items-start gap-4">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-koraku-panel ring-1 ring-neutral-200/80">
                  <MessageCircle className="h-5 w-5 text-koraku-ink" strokeWidth={2} aria-hidden />
                </div>
                <div>
                  <h2 className="text-lg font-bold tracking-tight text-koraku-ink">
                    Link your number
                  </h2>
                  <p className="mt-1 text-sm font-medium text-koraku-muted">
                    We send a short code to confirm you own the phone you text from.
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wide text-neutral-500">
                    Your phone
                  </label>
                  <p className="mt-1 text-sm font-medium text-neutral-600">
                    Use E.164 format, e.g. +14155551234
                  </p>
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className={korakuUi.input}
                    placeholder="+1…"
                    disabled={!status.configured}
                  />
                </div>

                <KorakuButton
                  fullWidth
                  disabled={busy || !phone.trim() || !status.configured}
                  onClick={() => void startVerify()}
                >
                  {busy ? "Sending…" : "Send verification code"}
                </KorakuButton>

                {sent ? (
                  <p className="rounded-2xl bg-koraku-panel px-4 py-3 text-xs font-medium leading-relaxed text-neutral-600 ring-1 ring-neutral-200/80">
                    Check iMessage or SMS for your code. You can also reply with{" "}
                    <code className="rounded-md bg-white px-1.5 py-0.5 font-mono text-[12px] text-koraku-ink ring-1 ring-neutral-200/80">
                      KORAKU-######
                    </code>{" "}
                    to the Koraku number.
                  </p>
                ) : null}

                <div className="border-t border-neutral-200/80 pt-4">
                  <label className="block text-xs font-semibold uppercase tracking-wide text-neutral-500">
                    Verification code
                  </label>
                  <input
                    type="text"
                    inputMode="numeric"
                    maxLength={12}
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    className="mt-3 w-full rounded-2xl border border-neutral-200/80 bg-koraku-panel px-4 py-3 text-[15px] font-medium text-koraku-ink outline-none focus:border-neutral-300 focus:bg-white focus:ring-2 focus:ring-neutral-200/80"
                    placeholder="6 digits"
                  />
                  <KorakuButton
                    variant="secondary"
                    fullWidth
                    disabled={busy || !phone.trim() || !code.trim()}
                    onClick={() => void confirmVerify()}
                    className="mt-4"
                  >
                    Confirm and link
                  </KorakuButton>
                </div>
              </div>
            </section>
          )}

          <section className="rounded-[28px] bg-white/80 p-6 ring-1 ring-neutral-200/80">
            <h2 className="text-sm font-bold text-koraku-ink">Getting started</h2>
            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm font-medium leading-relaxed text-neutral-600">
              <li>
                Add the Koraku number to your contacts, then send one message from your real
                phone.
              </li>
              <li>Link the same number here — not a placeholder or test line.</li>
              <li>
                Your administrator must point inbound messaging webhooks at this Koraku server
                (see server docs for setup).
              </li>
            </ol>
          </section>
        </div>
    </KorakuAppPage>
  );
}
