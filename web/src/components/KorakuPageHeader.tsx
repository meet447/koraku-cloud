import type { ReactNode } from "react";

type KorakuPageHeaderProps = {
  eyebrow: string;
  title: string;
  description: ReactNode;
  action?: ReactNode;
  density?: "default" | "compact";
};

export function KorakuPageHeader({
  eyebrow,
  title,
  description,
  action,
  density = "default",
}: KorakuPageHeaderProps) {
  const compact = density === "compact";
  return (
    <header
      className={
        compact
          ? "flex flex-col justify-between gap-3 sm:flex-row sm:items-center"
          : "flex flex-col justify-between gap-6 sm:flex-row sm:items-end"
      }
    >
      <div className="min-w-0">
        <p
          className={
            compact
              ? "text-[11px] font-bold uppercase tracking-[0.18em] text-orange-700"
              : "text-xs font-bold uppercase tracking-[0.22em] text-orange-700"
          }
        >
          {eyebrow}
        </p>
        <h1
          className={
            compact
              ? "mt-1 text-2xl font-bold leading-tight tracking-tight text-koraku-ink"
              : "mt-2 text-[2rem] font-bold leading-tight tracking-tight text-koraku-ink sm:text-4xl"
          }
        >
          {title}
        </h1>
        <p
          className={
            compact
              ? "mt-1 max-w-2xl text-sm font-medium leading-snug text-koraku-muted"
              : "mt-3 max-w-2xl text-sm font-medium leading-relaxed text-koraku-muted"
          }
        >
          {description}
        </p>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </header>
  );
}
