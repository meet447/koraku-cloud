"use client";

import Link from "next/link";
import { useState } from "react";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { KorakuAppPage } from "@/components/KorakuAppPage";
import { KorakuPageHeader } from "@/components/KorakuPageHeader";
import { KorakuAlert } from "@/components/KorakuAlert";
import { KorakuButton } from "@/components/KorakuButton";
import { PersonalizationSection } from "@/components/PersonalizationSection";
import { errorMessage } from "@/lib/error-message";
import { korakuUi } from "@/lib/koraku-ui";
import { KORAKU_COPY } from "@/lib/korakuBrand";

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
      setError(errorMessage(e, "Export failed"));
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
      setError(errorMessage(e, "Delete failed"));
    } finally {
      setBusy(null);
    }
  }

  return (
    <KorakuAppPage maxWidth="3xl">
        <KorakuPageHeader
          eyebrow="Settings"
          title="Profile and account"
          description="Personalize how Koraku talks to you, export data, and review privacy controls."
        />

        {message ? (
          <KorakuAlert variant="success" className="mt-6">
            {message}
          </KorakuAlert>
        ) : null}
        {error ? (
          <KorakuAlert variant="error" className="mt-6">
            {error}
          </KorakuAlert>
        ) : null}

        <div className="mt-8 space-y-4">
          <PersonalizationSection />

          <section className={korakuUi.card}>
            <h2 className="text-lg font-bold text-koraku-ink">Data export</h2>
            <p className="mt-2 text-sm font-medium leading-relaxed text-koraku-muted">
              Download chat threads, messages, personalization, automations, and run history{" "}
              {KORAKU_COPY.dataStoredInKoraku}.
            </p>
            <KorakuButton
              onClick={() => void exportData()}
              disabled={busy !== null}
              className="mt-4"
            >
              {busy === "export" ? "Preparing..." : "Export JSON"}
            </KorakuButton>
          </section>

          <section className="rounded-[28px] border border-red-200 bg-red-50 p-6">
            <h2 className="text-lg font-bold text-red-950">Delete Koraku app data</h2>
            <p className="mt-2 text-sm font-medium leading-relaxed text-red-800">
              This clears Koraku-owned rows for your account. Full auth account deletion
              and disconnection of third-party providers may still need admin/support action
              in the public beta.
            </p>
            <KorakuButton
              variant="destructive"
              onClick={() => setConfirmDeleteOpen(true)}
              disabled={busy !== null}
              className="mt-4"
            >
              {busy === "delete" ? "Deleting..." : "Delete app data"}
            </KorakuButton>
          </section>

          <ConfirmDialog
            open={confirmDeleteOpen}
            title="Delete Koraku app data?"
            message={KORAKU_COPY.deleteDataNote}
            confirmLabel="Delete"
            destructive
            onConfirm={() => void deleteData()}
            onCancel={() => setConfirmDeleteOpen(false)}
          />

          <section className="rounded-[28px] bg-koraku-panel p-6 ring-1 ring-neutral-200/80">
            <h2 className="text-lg font-bold text-koraku-ink">Privacy and retention</h2>
            <p className="mt-2 text-sm font-medium leading-relaxed text-koraku-muted">
              {KORAKU_COPY.privacyProcessing}
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
    </KorakuAppPage>
  );
}
