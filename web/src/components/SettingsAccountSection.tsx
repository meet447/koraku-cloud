"use client";

import Link from "next/link";
import { useState } from "react";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { KorakuAlert } from "@/components/KorakuAlert";
import { KorakuButton } from "@/components/KorakuButton";
import { errorMessage } from "@/lib/error-message";
import { korakuUi } from "@/lib/koraku-ui";
import { KORAKU_COPY } from "@/lib/korakuBrand";

export function SettingsAccountSection({
  embedded = false,
  hideIntro = false,
}: {
  embedded?: boolean;
  hideIntro?: boolean;
}) {
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
    <div className="space-y-3">
      {hideIntro ? null : (
        <>
          <h2 className="text-base font-bold text-koraku-ink">Account & data</h2>
          <p className="text-sm font-medium leading-snug text-koraku-muted">
            Export your Koraku data, delete app rows, and review privacy policies.
          </p>
        </>
      )}

      {message ? (
        <KorakuAlert variant="success">{message}</KorakuAlert>
      ) : null}
      {error ? <KorakuAlert variant="error">{error}</KorakuAlert> : null}

      <section className={embedded ? korakuUi.cardPanel : korakuUi.card}>
        <h3 className="text-base font-bold text-koraku-ink">Data export</h3>
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

      <section className="rounded-xl border border-red-200 bg-red-50 p-4">
        <h3 className="text-base font-bold text-red-950">Delete Koraku app data</h3>
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

      <section className={embedded ? korakuUi.cardPanel : korakuUi.card}>
        <h3 className="text-base font-bold text-koraku-ink">Privacy and retention</h3>
        <p className="mt-2 text-sm font-medium leading-relaxed text-koraku-muted">
          {KORAKU_COPY.privacyProcessing}
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link href="/privacy" className="text-sm font-bold text-orange-700 underline">
            Privacy Policy
          </Link>
          <Link href="/terms" className="text-sm font-bold text-orange-700 underline">
            Terms
          </Link>
          <Link href="/security" className="text-sm font-bold text-orange-700 underline">
            Security
          </Link>
          <Link href="/cookies" className="text-sm font-bold text-orange-700 underline">
            Cookies
          </Link>
          <Link href="/contact" className="text-sm font-bold text-orange-700 underline">
            Contact
          </Link>
        </div>
      </section>
    </div>
  );
}
