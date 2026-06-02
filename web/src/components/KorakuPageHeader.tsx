import type { ReactNode } from "react";

type KorakuPageHeaderProps = {
  eyebrow: string;
  title: string;
  description: ReactNode;
  action?: ReactNode;
};

export function KorakuPageHeader({
  eyebrow,
  title,
  description,
  action,
}: KorakuPageHeaderProps) {
  return (
    <header className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
      <div className="min-w-0">
        <p className="text-xs font-bold uppercase tracking-[0.22em] text-orange-700">
          {eyebrow}
        </p>
        <h1 className="mt-2 text-[2rem] font-bold leading-tight tracking-tight text-koraku-ink sm:text-4xl">
          {title}
        </h1>
        <p className="mt-3 max-w-2xl text-sm font-medium leading-relaxed text-koraku-muted">
          {description}
        </p>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </header>
  );
}
