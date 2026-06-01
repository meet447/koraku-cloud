"use client";

import { useEffect } from "react";
import clsx from "clsx";

export type ConfirmDialogProps = {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 backdrop-blur-[1px] px-4"
      onClick={onCancel}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="koraku-confirm-title"
        className="w-full max-w-md rounded-xl bg-white shadow-xl ring-1 ring-neutral-900/10"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-5 py-4">
          <h2
            id="koraku-confirm-title"
            className="text-base font-semibold text-neutral-900"
          >
            {title}
          </h2>
          <p className="mt-2 whitespace-pre-line text-sm text-neutral-700">
            {message}
          </p>
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-neutral-200 px-4 py-3">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md px-3 py-1.5 text-sm font-medium text-neutral-700 hover:bg-neutral-100"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            autoFocus
            className={clsx(
              "rounded-md px-3 py-1.5 text-sm font-semibold text-white shadow-sm",
              destructive
                ? "bg-red-600 hover:bg-red-700"
                : "bg-orange-600 hover:bg-orange-700",
            )}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
