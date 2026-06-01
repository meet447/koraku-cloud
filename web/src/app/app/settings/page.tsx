"use client";

import Link from "next/link";
import { useState } from "react";
import { ConfirmDialog } from "@/components/ConfirmDialog";

export default function SettingsPage() {
  const [busy, setBusy] = useState<"export" | "delete" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);

  async function exportData() {
    setBusy("export");
    setError(null);
    setMessage(null);
    try {
      const r = await fetch("/api/account/export", { cache: "no-store" });
      if (!r.ok) throw new Error(`Export failed (${r.status})`);
      const data = await r.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `koraku-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setMessage("Export generated.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setBusy(null);
    }
  }

  async function deleteData() {
    setConfirmDeleteOpen(false);
    setBusy("delete");
    setError(null);
    setMessage(null);
    try {
      const r = await fetch("/api/account/delete-data", { method: "POST" });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data?.error || `Delete failed (${r.status})`);
      setMessage(data?.note || "Koraku app data deleted.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="min-h-0 flex-1 overflow-y-auto px-6 py-10">
      <div className="mx-auto max-w-3xl">
        <p className="text-xs font-bold uppercase tracking-[0.22em] text-orange-700">
          Settings
        </p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight text-neutral-950">
          Trust and account controls.
        </h1>
        <p className="mt-3 text-sm font-medium leading-relaxed text-neutral-600">
          Export your Koraku data, clear app data, and review beta privacy expectations.
        </p>

        {message ? (
          <p className="mt-6 rounded-2xl bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800 ring-1 ring-emerald-200">
            {message}
          </p>
        ) : null}
        {error ? (
          <p className="mt-6 rounded-2xl bg-red-50 px-4 py-3 text-sm font-semibold text-red-800 ring-1 ring-red-200">
            {error}
          </p>
        ) : null}

        <div className="mt-8 space-y-4">
          <section className="rounded-[28px] bg-white p-6 shadow-sm ring-1 ring-neutral-200/80">
            <h2 className="text-lg font-bold text-neutral-950">Data export</h2>
            <p className="mt-2 text-sm font-medium leading-relaxed text-neutral-600">
              Download chat threads, messages, personalization, automations, and run history
              stored in Supabase for your account.
            </p>
            <button
              type="button"
              onClick={() => void exportData()}
              disabled={busy !== null}
              className="mt-4 rounded-full bg-neutral-950 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50"
            >
              {busy === "export" ? "Preparing..." : "Export JSON"}
            </button>
          </section>

          <section className="rounded-[28px] border border-red-200 bg-red-50 p-6">
            <h2 className="text-lg font-bold text-red-950">Delete Koraku app data</h2>
            <p className="mt-2 text-sm font-medium leading-relaxed text-red-800">
              This clears Koraku-owned rows for your account. Full auth account deletion
              and disconnection of third-party providers may still need admin/support action
              in the public beta.
            </p>
            <button
              type="button"
              onClick={() => setConfirmDeleteOpen(true)}
              disabled={busy !== null}
              className="mt-4 rounded-full bg-red-700 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50"
            >
              {busy === "delete" ? "Deleting..." : "Delete app data"}
            </button>
          </section>

          <ConfirmDialog
            open={confirmDeleteOpen}
            title="Delete Koraku app data?"
            message="This removes chat history, personalization, automations, and automation runs stored in Koraku. It does not delete your Supabase auth account or provider-side data."
            confirmLabel="Delete"
            destructive
            onConfirm={() => void deleteData()}
            onCancel={() => setConfirmDeleteOpen(false)}
          />

          <section className="rounded-[28px] bg-[#fbfaf6] p-6 ring-1 ring-neutral-200/80">
            <h2 className="text-lg font-bold text-neutral-950">Privacy and retention</h2>
            <p className="mt-2 text-sm font-medium leading-relaxed text-neutral-600">
              Koraku sends prompts and tool context to configured LLM providers and may route
              connected-app actions through Composio or workspace execution through Blaxel.
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Link href="/privacy" className="text-sm font-bold text-orange-700 underline">
                Privacy
              </Link>
              <Link href="/terms" className="text-sm font-bold text-orange-700 underline">
                Terms
              </Link>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
