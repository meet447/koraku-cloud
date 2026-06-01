"use client";

import { useCallback, useMemo, useState } from "react";
import clsx from "clsx";
import { Download, FileSpreadsheet, FileText, Loader2 } from "lucide-react";
import type { TimelineRow } from "@/lib/korakuReducer";
import { collectRunWorkspaceFileTouches } from "@/lib/workspaceAttachmentsFromTimeline";

function fileName(path: string) {
  return path.replace(/\\/g, "/").split("/").pop() || path;
}

function extOf(path: string) {
  const base = fileName(path);
  const i = base.lastIndexOf(".");
  return i >= 0 ? base.slice(i).toLowerCase() : "";
}

function FileKindIcon({ path }: { path: string }) {
  const ext = extOf(path);
  if (ext === ".csv" || ext === ".tsv" || ext === ".xlsx") {
    return (
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100">
        <FileSpreadsheet className="h-4 w-4" strokeWidth={1.5} aria-hidden />
      </span>
    );
  }
  if (ext === ".docx" || ext === ".doc") {
    return (
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-700 ring-1 ring-blue-100">
        <FileText className="h-4 w-4" strokeWidth={1.5} aria-hidden />
      </span>
    );
  }
  return (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-neutral-100 text-neutral-600 ring-1 ring-neutral-200/80">
      <FileText className="h-4 w-4" strokeWidth={1.5} aria-hidden />
    </span>
  );
}

/** Rounded file list + download actions for cloud workspace paths touched this turn. */
export function RunWorkspaceAttachments({
  timeline,
  serverSessionId,
}: {
  timeline: TimelineRow[];
  serverSessionId: string | null;
}) {
  const items = useMemo(() => collectRunWorkspaceFileTouches(timeline), [timeline]);
  const [busyPath, setBusyPath] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const download = useCallback(
    async (relPath: string) => {
      if (!serverSessionId) return;
      setDownloadError(null);
      setBusyPath(relPath);
      try {
        const q = new URLSearchParams({
          session_id: serverSessionId,
          path: relPath,
        });
        const res = await fetch(`/koraku-api/api/workspace/file/blob?${q}`, {
          credentials: "include",
        });
        if (!res.ok) {
          setDownloadError("Could not download this file.");
          return;
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = fileName(relPath);
        a.rel = "noopener";
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      } catch {
        setDownloadError("Could not download this file.");
      } finally {
        setBusyPath(null);
      }
    },
    [serverSessionId],
  );

  if (items.length === 0) return null;

  return (
    <div className="mt-4 rounded-2xl border border-neutral-200/80 bg-[#f0f0f2] px-3 py-2 shadow-sm ring-1 ring-black/[0.03]">
      <ul className="m-0 list-none space-y-0 divide-y divide-neutral-200/70 p-0">
        {items.map(({ path }) => {
          const canDl = Boolean(serverSessionId);
          const loading = busyPath === path;
          return (
            <li key={path} className="flex items-center gap-2.5 py-2.5 first:pt-1 last:pb-1">
              <FileKindIcon path={path} />
              <p
                className="min-w-0 flex-1 truncate text-[13px] font-medium text-neutral-800"
                title={path}
              >
                {fileName(path)}
              </p>
              <button
                type="button"
                disabled={!canDl || loading}
                title={canDl ? "Download" : "Sandbox session required to download files"}
                onClick={() => void download(path)}
                className={clsx(
                  "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-neutral-600 transition",
                  canDl && !loading
                    ? "bg-white shadow-sm ring-1 ring-neutral-200/70 hover:bg-neutral-50 hover:text-neutral-900"
                    : "cursor-not-allowed opacity-45",
                )}
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                ) : (
                  <Download className="h-4 w-4" strokeWidth={1.5} aria-hidden />
                )}
                <span className="sr-only">Download {fileName(path)}</span>
              </button>
            </li>
          );
        })}
      </ul>
      {!serverSessionId ? (
        <p className="border-t border-neutral-200/60 px-0.5 pb-0.5 pt-2 text-center text-[11px] leading-snug text-neutral-500">
          Sign in and send a message so this thread can download files from your session folder.
        </p>
      ) : downloadError ? (
        <p className="border-t border-neutral-200/60 px-0.5 pb-0.5 pt-2 text-center text-[11px] text-red-600">
          {downloadError}
        </p>
      ) : null}
    </div>
  );
}
