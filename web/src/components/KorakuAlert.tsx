import clsx from "clsx";
import type { ReactNode } from "react";

type KorakuAlertVariant = "error" | "success" | "warning" | "info";

const VARIANT_STYLES: Record<KorakuAlertVariant, string> = {
  error: "bg-red-50 text-red-800 ring-red-200/80",
  success: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  warning: "bg-amber-50 text-amber-950 ring-amber-200/80",
  info: "bg-koraku-panel text-koraku-ink ring-neutral-200/80",
};

export function KorakuAlert({
  variant,
  children,
  className,
  role = variant === "error" ? "alert" : "status",
}: {
  variant: KorakuAlertVariant;
  children: ReactNode;
  className?: string;
  role?: "alert" | "status";
}) {
  return (
    <p
      role={role}
      className={clsx(
        "rounded-2xl px-4 py-3 text-sm font-medium ring-1",
        VARIANT_STYLES[variant],
        className,
      )}
    >
      {children}
    </p>
  );
}
