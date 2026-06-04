"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";

type PptxPreviewer = {
  preview: (file: ArrayBuffer) => Promise<unknown>;
  destroy: () => void;
};

async function createPptxPreviewer(
  dom: HTMLElement,
  width: number,
  height: number,
): Promise<PptxPreviewer> {
  const { init } = await import("pptx-preview");
  return init(dom, { width, height, mode: "slide" });
}

function measureSlideSize(container: HTMLElement): { width: number; height: number } {
  const w = Math.max(280, Math.floor(container.clientWidth - 16));
  const h = Math.max(158, Math.floor(w * (9 / 16)));
  return { width: w, height: h };
}

/** Client-side PPTX slide preview (lazy-loads pptx-preview). */
export function PptxSlidePreview({ buffer }: { buffer: ArrayBuffer }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<PptxPreviewer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [slideSize, setSlideSize] = useState<{ width: number; height: number } | null>(
    null,
  );

  useLayoutEffect(() => {
    const el = hostRef.current;
    if (!el) return;
    setSlideSize(measureSlideSize(el));
    const ro = new ResizeObserver(() => {
      setSlideSize(measureSlideSize(el));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const el = hostRef.current;
    if (!el || !buffer.byteLength || !slideSize) return;

    let cancelled = false;
    setError(null);

    void (async () => {
      try {
        viewerRef.current?.destroy();
        viewerRef.current = null;
        el.replaceChildren();

        const viewer = await createPptxPreviewer(el, slideSize.width, slideSize.height);
        if (cancelled) {
          viewer.destroy();
          return;
        }
        viewerRef.current = viewer;
        await viewer.preview(buffer);
      } catch (e) {
        if (!cancelled) {
          setError(String((e as Error)?.message || e));
        }
      }
    })();

    return () => {
      cancelled = true;
      viewerRef.current?.destroy();
      viewerRef.current = null;
    };
  }, [buffer, slideSize]);

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-neutral-100">
      {error ? (
        <p className="shrink-0 border-b border-red-100 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </p>
      ) : null}
      <div ref={hostRef} className="min-h-0 flex-1 overflow-auto p-2 [&_.pptx-preview-wrapper]:mx-auto" />
    </div>
  );
}
