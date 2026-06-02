"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { MessageCircle, Loader2, CheckCircle2 } from "lucide-react";
import { APP_BASE } from "@/lib/app-path";
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
    const r = await fetch("/api/external/status", { credentials: "include" });
    if (!r.ok) return;
    setStatus((await r.json()) as ExternalStatus);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function startVerify() {
    setError(null);
    setBusy(true);
    try {
      const r = await fetch("/koraku-api/sendblue/verify/start", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phone.trim() }),
      });
      const j = (await r.json()) as { detail?: string; sent?: boolean };
      if (!r.ok) {
        setError(j.detail || "Could not send verification code");
        return;
      }
      setSent(Boolean(j.sent));
    } finally {
      setBusy(false);
    }
  }

  async function confirmVerify() {
    setError(null);
    setBusy(true);
    try {
      const r = await fetch("/koraku-api/sendblue/verify/confirm", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phone.trim(), code: code.trim() }),
      });
      const j = (await r.json()) as {
        detail?: string;
        imessage_thread_id?: string;
      };
      if (!r.ok) {
        setError(j.detail || "Invalid code");
        return;
      }
      await load();
      await shell.reloadSessions();
      if (j.imessage_thread_id) {
        shell.selectSession(j.imessage_thread_id);
      }
    } finally {
      setBusy(false);
    }
  }

  if (!status) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-neutral-500">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg px-6 py-10">
      <div className="mb-8 flex items-center gap-3">
        <MessageCircle className="h-8 w-8 text-violet-600" strokeWidth={1.5} />
        <div>
          <h1 className="text-xl font-semibold text-neutral-900">External</h1>
          <p className="text-sm text-neutral-500">
            Text Koraku from iMessage or SMS after you verify your number.
          </p>
        </div>
      </div>

      {!status.configured ? (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          SendBlue is not configured on this server. Add{" "}
          <code className="text-xs">SENDBLUE_API_KEY</code>,{" "}
          <code className="text-xs">SENDBLUE_API_SECRET</code>, and{" "}
          <code className="text-xs">SENDBLUE_FROM_NUMBER</code> to the API environment.
        </p>
      ) : null}

      {status.from_number ? (
        <p className="mb-6 rounded-xl border border-neutral-200 bg-white px-4 py-3 text-sm text-neutral-700">
          <span className="font-medium text-neutral-900">Koraku number: </span>
          <a
            href={`sms:${encodeURIComponent(status.from_number)}`}
            className="text-violet-700 underline"
          >
            {status.from_number}
          </a>
        </p>
      ) : null}

      {status.linked ? (
        <div className="space-y-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-4">
          <div className="flex items-center gap-2 text-emerald-800">
            <CheckCircle2 className="h-5 w-5" />
            <span className="font-medium">Phone linked</span>
          </div>
          <p className="text-sm text-emerald-900">{status.phone_e164}</p>
          <Link
            href={APP_BASE}
            onClick={() => {
              if (status.imessage_thread_id) {
                shell.selectSession(status.imessage_thread_id);
              }
            }}
            className="inline-block text-sm font-medium text-violet-700 underline"
          >
            Open iMessage chat in Koraku
          </Link>
        </div>
      ) : (
        <div className="space-y-4 rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
          <label className="block text-sm font-medium text-neutral-800">
            Your phone (E.164, e.g. +14155551234)
          </label>
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"
            placeholder="+1…"
          />
          <button
            type="button"
            disabled={busy || !phone.trim() || !status.configured}
            onClick={() => void startVerify()}
            className="w-full rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {busy ? "Sending…" : "Send verification code"}
          </button>
          {sent ? (
            <p className="text-xs text-neutral-500">
              Check iMessage/SMS for your code, or reply{" "}
              <code className="rounded bg-neutral-100 px-1">KORAKU-######</code> to the Koraku
              number.
            </p>
          ) : null}
          <label className="block pt-2 text-sm font-medium text-neutral-800">
            Verification code
          </label>
          <input
            type="text"
            inputMode="numeric"
            maxLength={12}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"
            placeholder="6 digits"
          />
          <button
            type="button"
            disabled={busy || !phone.trim() || !code.trim()}
            onClick={() => void confirmVerify()}
            className="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm font-medium text-neutral-900 disabled:opacity-50"
          >
            Confirm and link
          </button>
        </div>
      )}

      {error ? (
        <p className="mt-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}

      <div className="mt-8 space-y-2 rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-xs text-neutral-600">
        <p className="font-medium text-neutral-800">SendBlue Free Tier (required for iMessage)</p>
        <ol className="list-decimal space-y-1 pl-4">
          <li>
            <code className="rounded bg-white px-1">sendblue add-contact +1…</code> — your real
            number, then text the Koraku line once.
          </li>
          <li>Link the same number here on External (not +14155551234).</li>
          <li>
            Webhook:{" "}
            <code className="rounded bg-white px-1">sendblue webhooks set-receive https://…/sendblue/webhook</code>{" "}
            → public API :8000 (e.g. ngrok). See{" "}
            <code className="rounded bg-white px-1">docs/SENDBLUE.md</code>.
          </li>
        </ol>
      </div>
    </div>
  );
}
