"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Check,
  ChevronDown,
  Cpu,
  Flame,
  Globe,
  Settings,
  Sparkles,
} from "lucide-react";
import clsx from "clsx";
import { APP_BASE } from "@/lib/app-path";

const STORAGE_KEY = "koraku_provider_model";

type ModelCatalogEntry = {
  id: string;
  logo_url?: string;
  label?: string;
};

type Block = {
  id: string;
  label?: string;
  configured: boolean;
  models: string[];
  /** When set (e.g. Fireworks), drives order/labels/logos for the composer picker. */
  entries?: ModelCatalogEntry[];
};

type ChatModelsResponse = {
  providers?: Block[];
  models?: string[];
  active_provider?: string;
  default_model?: string;
};

export type ModelOption = {
  value: string;
  providerId: string;
  modelId: string;
  disabled: boolean;
  group?: string;
  /** Catalog model name (shown in picker, trigger, and message footer) */
  title: string;
  /** Provider-supplied logo (e.g. Fireworks catalog) */
  logoUrl?: string;
};

function providerLabel(id: string, block?: Block): string {
  if (block?.label?.trim()) return block.label.trim();
  if (id === "custom") return "Custom endpoint";
  if (id === "fireworks") return "Fireworks";
  return id.charAt(0).toUpperCase() + id.slice(1);
}

function shortModelTitle(raw: string): string {
  const tail = raw.includes("/") ? (raw.split("/").pop() ?? raw) : raw;
  return tail
    .replace(/\.(gguf|safetensors)$/i, "")
    .replace(/[-_]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function ModelRowIcon({
  providerId,
  modelId,
  logoUrl,
}: {
  providerId: string;
  modelId: string;
  logoUrl?: string;
}) {
  if (logoUrl) {
    /* No frame/shadow — logo only (composer + chat chrome). */
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={logoUrl}
        alt=""
        className="h-7 w-7 shrink-0 object-contain"
        loading="lazy"
        referrerPolicy="no-referrer-when-downgrade"
      />
    );
  }
  const m = modelId.toLowerCase();
  const p = providerId.toLowerCase();
  if (m.includes("sonnet") || m.includes("opus") || m.includes("claude")) {
    return (
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-800">
        <Sparkles className="h-4 w-4" aria-hidden />
      </span>
    );
  }
  if (m.includes("gpt") || m.includes("openai")) {
    return (
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-neutral-900 text-[10px] font-bold text-white">
        AI
      </span>
    );
  }
  if (p === "fireworks") {
    return (
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-orange-100 text-orange-800">
        <Flame className="h-4 w-4" aria-hidden />
      </span>
    );
  }
  if (p === "custom" || p === "openai") {
    return (
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-sky-100 text-sky-800">
        <Globe className="h-4 w-4" aria-hidden />
      </span>
    );
  }
  return (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-neutral-100 text-neutral-600">
      <Cpu className="h-4 w-4" aria-hidden />
    </span>
  );
}

export function ModelSelect({
  disabled,
  onReady,
}: {
  disabled?: boolean;
  /** Third arg is a short display label for the footer (matches old select label). */
  onReady?: (provider: string, model: string, displayLabel: string) => void;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  const [options, setOptions] = useState<ModelOption[]>([]);
  const [loaded, setLoaded] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const onReadyRef = useRef(onReady);
  onReadyRef.current = onReady;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch("/koraku-api/api/chat-models");
        const d = (await r.json()) as ChatModelsResponse;
        const next: ModelOption[] = [];
        const blocks = d.providers || [];
        if (blocks.length) {
          for (const block of blocks) {
            const entries: ModelCatalogEntry[] = block.entries?.length
              ? block.entries
              : (block.models || []).map((id) => ({ id }));
            for (const row of entries) {
              const m = row.id;
              const modelLbl =
                (row.label || "").trim() || shortModelTitle(m);
              const prov = providerLabel(block.id, block);
              const title = block.configured
                ? modelLbl
                : `${modelLbl} · not configured`;
              next.push({
                value: `${block.id}\t${m}`,
                providerId: block.id,
                modelId: m,
                disabled: !block.configured,
                group: prov,
                title,
                logoUrl: row.logo_url,
              });
            }
          }
        } else {
          const ap = d.active_provider || "fireworks";
          for (const m of d.models || []) {
            const modelLbl = shortModelTitle(m);
            const prov = providerLabel(ap);
            next.push({
              value: `${ap}\t${m}`,
              providerId: ap,
              modelId: m,
              disabled: false,
              group: prov,
              title: modelLbl,
              logoUrl: undefined,
            });
          }
        }
        if (cancelled) return;
        setOptions(next);
        const saved =
          typeof window !== "undefined"
            ? localStorage.getItem(STORAGE_KEY)
            : null;
        const pickFirstEnabled = () => next.find((o) => !o.disabled)?.value ?? "";
        let chosen = pickFirstEnabled();
        if (saved && next.some((o) => o.value === saved && !o.disabled)) {
          chosen = saved;
        }
        setValue(chosen);
        setLoaded(true);
        const [p, m] = chosen.split("\t");
        const opt = next.find((o) => o.value === chosen);
        onReadyRef.current?.(p || "", m || "", opt?.title ?? "");
      } catch {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const selected = options.find((o) => o.value === value);

  const pick = useCallback((v: string) => {
    const o = options.find((x) => x.value === v);
    if (!o || o.disabled) return;
    setValue(v);
    setOpen(false);
    const [p, m] = v.split("\t");
    onReadyRef.current?.(p || "", m || "", o.title);
    try {
      localStorage.setItem(STORAGE_KEY, v);
    } catch {
      /* ignore */
    }
  }, [options]);

  const triggerLabel = selected?.title ?? "Select model";

  return (
    <div ref={rootRef} className="relative min-w-0">
      <button
        type="button"
        disabled={disabled || !loaded || options.length === 0}
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={() => setOpen((o) => !o)}
        className={clsx(
          "flex h-8 w-full min-w-0 max-w-[min(100vw-8rem,19rem)] items-center gap-1.5 rounded-full border border-neutral-200/50 bg-white/85 py-0.5 pr-2 pl-1.5 text-left shadow-sm backdrop-blur-sm transition",
          "hover:border-neutral-300/60 hover:bg-white/95",
          "disabled:cursor-not-allowed disabled:opacity-50",
          open && "border-neutral-300 ring-2 ring-neutral-200/80",
        )}
      >
        {selected ? (
          <ModelRowIcon
            providerId={selected.providerId}
            modelId={selected.modelId}
            logoUrl={selected.logoUrl}
          />
        ) : (
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-neutral-100 text-neutral-500">
            <Cpu className="h-4 w-4" />
          </span>
        )}
        <span className="min-w-0 flex-1 truncate text-xs font-semibold text-koraku-ink">
          {triggerLabel}
        </span>
        <ChevronDown
          className={clsx(
            "h-4 w-4 shrink-0 text-neutral-400 transition",
            open && "rotate-180",
          )}
        />
      </button>

      {open && options.length > 0 ? (
        <div
          role="listbox"
          className="absolute bottom-full left-0 z-50 mb-2 w-[min(calc(100vw-2rem),18rem)] overflow-hidden rounded-2xl border border-neutral-200/90 bg-white py-1.5 shadow-lg"
        >
          <div className="max-h-[min(70vh,20rem)] overflow-y-auto overscroll-contain px-1">
            {options.map((o) => {
              const isSel = o.value === value;
              return (
                <button
                  key={o.value}
                  type="button"
                  role="option"
                  aria-selected={isSel}
                  disabled={o.disabled}
                  onClick={() => pick(o.value)}
                  className={clsx(
                    "flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left transition",
                    isSel && "bg-neutral-100",
                    o.disabled
                      ? "cursor-not-allowed opacity-40"
                      : "hover:bg-neutral-50",
                  )}
                >
                  <ModelRowIcon
                    providerId={o.providerId}
                    modelId={o.modelId}
                    logoUrl={o.logoUrl}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-semibold text-koraku-ink">
                      {o.title}
                    </span>
                  </span>
                  {isSel ? (
                    <Check
                      className="h-4 w-4 shrink-0 text-koraku-ink"
                      aria-hidden
                    />
                  ) : (
                    <span className="h-4 w-4 shrink-0" aria-hidden />
                  )}
                </button>
              );
            })}
          </div>
          <div className="mx-2 my-1.5 border-t border-neutral-100" />
          <button
            type="button"
            className="mx-1 flex w-[calc(100%-0.5rem)] items-center gap-3 rounded-xl px-2 py-2 text-left text-sm font-semibold text-neutral-600 hover:bg-neutral-50"
            onClick={() => {
              setOpen(false);
              router.push(`${APP_BASE}/models`);
            }}
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-neutral-100 text-neutral-500">
              <Settings className="h-4 w-4" />
            </span>
            Configure
          </button>
        </div>
      ) : null}
    </div>
  );
}
