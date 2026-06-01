"use client";

import clsx from "clsx";
import Image from "next/image";

const BRAND_SRC = "/icon.png";
const NEW_CHAT_BRAND_SRC = "/butterfly-pixel.gif";

export function BrandMark({
  size,
  className,
  priority,
  variant = "default",
}: {
  size: number;
  className?: string;
  /** Set on first-paint surfaces (sidebar, hero). */
  priority?: boolean;
  /** `newChat` uses the pixel butterfly GIF on the empty chat screen. */
  variant?: "default" | "newChat";
}) {
  if (variant === "newChat") {
    return (
      <Image
        src={NEW_CHAT_BRAND_SRC}
        alt="Koraku"
        width={size}
        height={size}
        className={clsx("shrink-0 object-contain", className)}
        priority={priority}
        sizes={`${size}px`}
        unoptimized
      />
    );
  }

  return (
    <Image
      src={BRAND_SRC}
      alt="Koraku"
      width={size}
      height={size}
      className={clsx("shrink-0 object-contain", className)}
      priority={priority}
      sizes={`${size}px`}
    />
  );
}
