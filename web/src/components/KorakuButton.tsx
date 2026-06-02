import clsx from "clsx";
import type { ButtonHTMLAttributes } from "react";

export type KorakuButtonVariant = "primary" | "secondary" | "destructive";
export type KorakuButtonSize = "sm" | "md" | "lg";

const VARIANT: Record<KorakuButtonVariant, string> = {
  primary:
    "bg-neutral-900 text-white shadow-sm hover:bg-neutral-800 disabled:bg-neutral-300",
  secondary:
    "border border-neutral-200/90 bg-white text-koraku-ink shadow-sm hover:bg-neutral-50",
  destructive: "bg-red-700 text-white hover:bg-red-800",
};

const SIZE: Record<KorakuButtonSize, string> = {
  sm: "px-4 py-2 text-sm",
  md: "px-5 py-2.5 text-sm",
  lg: "px-8 py-3 text-sm",
};

export function korakuButtonClass({
  variant = "primary",
  size = "md",
  fullWidth = false,
  className,
}: {
  variant?: KorakuButtonVariant;
  size?: KorakuButtonSize;
  fullWidth?: boolean;
  className?: string;
} = {}) {
  return clsx(
    "inline-flex items-center justify-center rounded-full font-semibold transition disabled:cursor-not-allowed disabled:opacity-50",
    VARIANT[variant],
    SIZE[size],
    fullWidth && "w-full",
    className,
  );
}

export function KorakuButton({
  variant = "primary",
  size = "md",
  fullWidth = false,
  className,
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: KorakuButtonVariant;
  size?: KorakuButtonSize;
  fullWidth?: boolean;
}) {
  return (
    <button
      type={type}
      className={korakuButtonClass({ variant, size, fullWidth, className })}
      {...props}
    />
  );
}
