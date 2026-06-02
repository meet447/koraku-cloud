import clsx from "clsx";
import { Search } from "lucide-react";

type KorakuSearchInputProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  /** Full-width pill for page headers; compact for sidebars and panels. */
  variant?: "page" | "compact";
  className?: string;
  "aria-label"?: string;
};

export function KorakuSearchInput({
  value,
  onChange,
  placeholder,
  variant = "page",
  className,
  "aria-label": ariaLabel,
}: KorakuSearchInputProps) {
  const compact = variant === "compact";

  return (
    <div className={clsx("relative min-w-0", className)}>
      <Search
        className={clsx(
          "pointer-events-none absolute top-1/2 -translate-y-1/2 text-neutral-400",
          compact ? "left-3 h-4 w-4" : "left-4 h-[18px] w-[18px]",
        )}
        strokeWidth={2}
        aria-hidden
      />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={ariaLabel ?? placeholder}
        className={clsx(
          "w-full border border-neutral-200/90 bg-white font-medium text-koraku-ink shadow-sm outline-none transition placeholder:text-neutral-400 focus:border-neutral-300 focus:ring-2 focus:ring-orange-200/60",
          compact
            ? "rounded-xl py-2.5 pl-9 pr-3 text-sm focus:ring-neutral-200/80"
            : "rounded-full py-3.5 pl-11 pr-5 text-[15px]",
        )}
      />
    </div>
  );
}
