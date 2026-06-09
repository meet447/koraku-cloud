"use client";

import clsx from "clsx";
import { Check, Loader2, Sparkles } from "lucide-react";
import type { ProfileLinkResult } from "@/lib/profile-links";
import { korakuUi } from "@/lib/koraku-ui";

export type AboutGeneratePhase = "fetching" | "writing" | "complete";

export type PendingProfileLink = {
  label: string;
  url: string;
};

type Props = {
  phase: AboutGeneratePhase;
  statusMessage: string;
  displayedAbout: string;
  pendingLinks: PendingProfileLink[];
  linkResults: ProfileLinkResult[];
};

function LinkStatusRow({
  label,
  phase,
  result,
}: {
  label: string;
  phase: AboutGeneratePhase;
  result?: ProfileLinkResult;
}) {
  const waiting = phase === "fetching" && !result;
  const ok = result?.status === "ok";
  const failed = result?.status === "failed";

  return (
    <li
      className={clsx(
        "flex items-center gap-3 rounded-xl border px-3 py-2.5 transition-colors",
        waiting && "border-neutral-200/80 bg-white",
        ok && "border-emerald-200/80 bg-emerald-50/50",
        failed && "border-amber-200/80 bg-amber-50/40",
        result && !ok && !failed && "border-neutral-200/80 bg-white",
      )}
    >
      <div
        className={clsx(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
          waiting && "bg-neutral-100",
          ok && "bg-emerald-100 text-emerald-700",
          failed && "bg-amber-100 text-amber-700",
        )}
      >
        {waiting ? (
          <Loader2 className="h-4 w-4 animate-spin text-neutral-500" aria-hidden />
        ) : ok ? (
          <Check className="h-4 w-4" aria-hidden />
        ) : (
          <span className="text-xs font-bold">!</span>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-koraku-ink">{label}</p>
        <p className="text-xs font-medium text-koraku-muted">
          {waiting
            ? "Reading public page…"
            : ok
              ? "Fetched"
              : failed
                ? result?.error || "Could not read — link saved"
                : "Saved"}
        </p>
      </div>
    </li>
  );
}

export function OnboardingAboutGenerateView({
  phase,
  statusMessage,
  displayedAbout,
  pendingLinks,
  linkResults,
}: Props) {
  const writing = phase === "writing" || phase === "complete";
  const showCursor = phase === "writing";

  return (
    <div
      className="relative overflow-hidden rounded-2xl border border-orange-200/60 bg-gradient-to-br from-orange-50/80 via-white to-neutral-50 p-6 sm:p-8"
      aria-busy={phase !== "complete"}
      aria-live="polite"
    >
      <div
        className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-orange-200/30 blur-3xl"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -bottom-20 -left-10 h-40 w-40 rounded-full bg-neutral-200/40 blur-3xl"
        aria-hidden
      />

      <div className="relative flex flex-wrap items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white shadow-sm ring-1 ring-orange-200/70">
          {phase === "complete" ? (
            <Check className="h-5 w-5 text-emerald-600" aria-hidden />
          ) : (
            <Loader2 className="h-5 w-5 animate-spin text-orange-700" aria-hidden />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-2 text-sm font-bold text-koraku-ink">
            <Sparkles className="h-4 w-4 text-orange-600" aria-hidden />
            Building your profile
          </p>
          <p className="mt-0.5 text-sm font-medium text-koraku-muted">{statusMessage}</p>
        </div>
      </div>

      {pendingLinks.length > 0 ? (
        <ul className="relative mt-6 grid gap-2 sm:grid-cols-2">
          {pendingLinks.map((link) => {
            const result = linkResults.find(
              (row) => row.url === link.url || row.label === link.label,
            );
            return (
              <LinkStatusRow
                key={`${link.label}-${link.url}`}
                label={link.label}
                phase={phase}
                result={result}
              />
            );
          })}
        </ul>
      ) : null}

      {writing ? (
        <div className="relative mt-8">
          <p className={korakuUi.fieldLabel}>Describe yourself</p>
          <div
            className={clsx(
              "relative mt-3 min-h-[10.5rem] rounded-xl border bg-white/90 px-4 py-3.5 shadow-sm transition",
              phase === "complete" ? "border-emerald-200/90" : "border-neutral-300/90",
            )}
          >
            <p className="whitespace-pre-wrap text-sm font-medium leading-relaxed text-koraku-ink">
              {displayedAbout}
              {showCursor ? (
                <span
                  className="ml-0.5 inline-block h-[1.1em] w-0.5 animate-pulse bg-orange-600 align-[-0.15em]"
                  aria-hidden
                />
              ) : null}
            </p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
