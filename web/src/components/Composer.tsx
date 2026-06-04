"use client";

import Image from "next/image";
import { useCallback, useRef, useState } from "react";
import clsx from "clsx";
import { ArrowUp, Plus, X } from "lucide-react";
import {
  readComposerImagesFromFiles,
  type ComposerImage,
} from "@/lib/composer-images";
import { ModelSelect } from "./ModelSelect";

const MAX_IMAGES = 8;

export type { ComposerImage };

export function Composer({
  busy,
  disabled = false,
  placeholder = "Ask anything",
  onSend,
}: {
  busy: boolean;
  /** When true, blocks input (e.g. app or thread messages still loading). */
  disabled?: boolean;
  /** Shown in the textarea when not focused on empty (e.g. follow-up while streaming). */
  placeholder?: string;
  onSend: (
    text: string,
    provider: string,
    model: string,
    dropdownModelLabel: string,
    images: ComposerImage[],
  ) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const modelRef = useRef({ provider: "", model: "", dropdownModelLabel: "" });
  const [text, setText] = useState("");
  const [images, setImages] = useState<ComposerImage[]>([]);
  const syncModel = useCallback((p: string, m: string, label: string) => {
    modelRef.current = { provider: p, model: m, dropdownModelLabel: label };
  }, []);

  const removeImage = (id: string) => {
    setImages((prev) => {
      const next = prev.filter((x) => x.id !== id);
      for (const row of prev) {
        if (row.id === id) URL.revokeObjectURL(row.previewUrl);
      }
      return next;
    });
  };

  const onFiles = (files: FileList | null) => {
    if (!files?.length) return;
    void (async () => {
      const rows = await readComposerImagesFromFiles(files, MAX_IMAGES);
      if (!rows.length) return;
      setImages((prev) => [...prev, ...rows].slice(0, MAX_IMAGES));
    })();
  };

  const submit = () => {
    if (disabled) return;
    const t = text.trim();
    const ready = images.filter((i) => i.data.length > 0);
    if (!t && ready.length === 0) return;
    const { provider, model, dropdownModelLabel } = modelRef.current;
    onSend(t, provider, model, dropdownModelLabel, ready);
    setText("");
    for (const row of images) URL.revokeObjectURL(row.previewUrl);
    setImages([]);
  };

  const canSend = text.trim().length > 0 || images.some((i) => i.data.length > 0);

  return (
    <div
      className={clsx(
        "pointer-events-auto mx-auto w-full min-w-0 max-w-3xl px-4 pb-1 pt-0.5",
        disabled && "opacity-55",
      )}
    >
      <input
        ref={fileRef}
        type="file"
        accept="image/jpeg,image/png,image/gif,image/webp"
        multiple
        className="sr-only"
        aria-hidden
        tabIndex={-1}
        onChange={(e) => {
          onFiles(e.target.files);
          e.target.value = "";
        }}
      />
      <div
        className={clsx(
          "rounded-2xl border p-2 shadow-[0_8px_32px_-8px_rgb(0_0_0_/_0.1)] transition-[border-color,box-shadow,background-color] duration-300",
          busy && !disabled
            ? "koraku-composer-pulse border-orange-200/55 bg-[#ebe9e4]"
            : "border-neutral-200/70 bg-[#ebe9e4]",
        )}
        aria-busy={busy || disabled}
      >
        {images.length > 0 ? (
          <div className="mb-1.5 flex flex-wrap gap-1.5 px-0.5">
            {images.map((img) => (
              <div
                key={img.id}
                className="relative h-14 w-14 overflow-hidden rounded-lg border border-neutral-200/80 bg-white"
              >
                <Image
                  src={img.previewUrl}
                  alt=""
                  width={56}
                  height={56}
                  unoptimized
                  className="h-full w-full object-cover"
                />
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => removeImage(img.id)}
                  className="absolute right-0.5 top-0.5 flex h-6 w-6 items-center justify-center rounded-full bg-neutral-900/85 text-white shadow hover:bg-neutral-800 disabled:opacity-50"
                  aria-label="Remove image"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        ) : null}
        <textarea
          rows={2}
          aria-label={placeholder}
          value={text}
          disabled={disabled}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (disabled) return;
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder={placeholder}
          className="min-h-[2.75rem] w-full resize-none bg-transparent px-2 py-1 text-[14px] leading-snug text-koraku-ink placeholder:text-neutral-400 focus:outline-none disabled:cursor-not-allowed"
        />
        <div className="mt-1.5 flex min-w-0 flex-wrap items-center justify-between gap-1.5 pt-1">
          <div className="flex min-w-0 flex-wrap items-center gap-1.5">
            <button
              type="button"
              disabled={disabled || images.length >= MAX_IMAGES}
              onClick={() => fileRef.current?.click()}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-neutral-200 bg-white text-neutral-600 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
              aria-label="Add images"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>
          <div
            className={clsx(
              "flex min-w-0 shrink-0 items-center gap-2",
              disabled && "pointer-events-none opacity-60",
            )}
          >
            <ModelSelect onReady={syncModel} />
            <button
              type="button"
              onClick={submit}
              disabled={disabled || !canSend}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-900 text-white shadow-sm transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-300"
              aria-label="Send"
            >
              <ArrowUp className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
