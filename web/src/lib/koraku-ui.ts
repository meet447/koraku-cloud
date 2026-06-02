/** Shared Tailwind class strings for Koraku app UI. */
export const korakuUi = {
  card: "rounded-[28px] bg-white p-6 shadow-sm ring-1 ring-neutral-200/80",
  cardPanel: "rounded-2xl border border-neutral-200/80 bg-koraku-panel p-5",
  input:
    "w-full rounded-2xl border border-neutral-200/80 bg-white px-4 py-3 text-[15px] font-medium text-koraku-ink outline-none focus:border-neutral-300 focus:ring-2 focus:ring-neutral-200/80 disabled:opacity-50",
  textarea:
    "w-full resize-y rounded-2xl border border-neutral-200/80 bg-white px-4 py-3 text-[15px] font-medium leading-relaxed text-koraku-ink outline-none focus:border-neutral-300 focus:ring-2 focus:ring-neutral-200/80 disabled:opacity-50",
  fieldLabel: "block text-xs font-semibold uppercase tracking-wide text-neutral-500",
} as const;

export type KorakuAppPageWidth = "2xl" | "3xl" | "4xl" | "5xl";

export const korakuAppPageMaxWidth: Record<KorakuAppPageWidth, string> = {
  "2xl": "max-w-2xl",
  "3xl": "max-w-3xl",
  "4xl": "max-w-4xl",
  "5xl": "max-w-5xl",
};
