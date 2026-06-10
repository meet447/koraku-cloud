"use client";

import Image from "next/image";
import { useCallback, useRef, useState } from "react";
import clsx from "clsx";
import { ArrowUp, FileText, Plus, X } from "lucide-react";
import {
  readComposerAttachmentsFromFiles,
  isComposerAttachmentFile,
  type ComposerAttachment,
} from "@/lib/composer-attachments";
import {
  readComposerImagesFromFiles,
  type ComposerImage,
} from "@/lib/composer-images";
import { ModelSelect } from "./ModelSelect";

const MAX_IMAGES = 8;
const MAX_ATTACHMENTS = 4;

export type { ComposerImage, ComposerAttachment };

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
    attachments: ComposerAttachment[],
  ) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const modelRef = useRef({ provider: "", model: "", dropdownModelLabel: "" });
  const [text, setText] = useState("");
  const [images, setImages] = useState<ComposerImage[]>([]);
  const [attachments, setAttachments] = useState<ComposerAttachment[]>([]);
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

  const removeAttachment = (id: string) => {
    setAttachments((prev) => prev.filter((x) => x.id !== id));
  };

  const onFiles = (files: FileList | null) => {
    if (!files?.length) return;
    void (async () => {
      const list = Array.from(files);
      const imageFiles = list.filter((f) => !isComposerAttachmentFile(f));
      const docFiles = list.filter((f) => isComposerAttachmentFile(f));
      if (imageFiles.length) {
        const rows = await readComposerImagesFromFiles(imageFiles, MAX_IMAGES);
        if (rows.length) {
          setImages((prev) => [...prev, ...rows].slice(0, MAX_IMAGES));
        }
      }
      if (docFiles.length) {
        const rows = await readComposerAttachmentsFromFiles(docFiles, MAX_ATTACHMENTS);
        if (rows.length) {
          setAttachments((prev) => [...prev, ...rows].slice(0, MAX_ATTACHMENTS));
        }
      }
    })();
  };

  const submit = () => {
    if (disabled) return;
    const t = text.trim();
    const readyImages = images.filter((i) => i.data.length > 0);
    const readyAttachments = attachments.filter((a) => a.data.length > 0);
    if (!t && readyImages.length === 0 && readyAttachments.length === 0) return;
    const { provider, model, dropdownModelLabel } = modelRef.current;
    onSend(t, provider, model, dropdownModelLabel, readyImages, readyAttachments);
    setText("");
    for (const row of images) URL.revokeObjectURL(row.previewUrl);
    setImages([]);
    setAttachments([]);
  };

  const canSend =
    text.trim().length > 0 ||
    images.some((i) => i.data.length > 0) ||
    attachments.some((a) => a.data.length > 0);

  const atFileLimit =
    images.length >= MAX_IMAGES && attachments.length >= MAX_ATTACHMENTS;

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
        accept="image/jpeg,image/png,image/gif,image/webp,.pdf,.docx,.txt,.md,.csv,application/pdf,text/plain,text/markdown,text/csv,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
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
                  title="Remove image"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        ) : null}
        {attachments.length > 0 ? (
          <div className="mb-1.5 flex flex-wrap gap-1.5 px-0.5">
            {attachments.map((att) => (
              <div
                key={att.id}
                className="flex max-w-full items-center gap-1.5 rounded-lg border border-neutral-200/80 bg-white px-2 py-1.5 text-xs text-neutral-700"
              >
                <FileText className="h-3.5 w-3.5 shrink-0 text-neutral-500" />
                <span className="truncate">{att.filename}</span>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => removeAttachment(att.id)}
                  className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-neutral-500 hover:bg-neutral-100 hover:text-neutral-800 disabled:opacity-50"
                  aria-label={`Remove ${att.filename}`}
                >
                  <X className="h-3 w-3" />
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
              disabled={disabled || atFileLimit}
              onClick={() => fileRef.current?.click()}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-neutral-200 bg-white text-neutral-600 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
              aria-label="Add images or documents"
              title="Add images or documents"
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
              title="Send"
            >
              <ArrowUp className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
