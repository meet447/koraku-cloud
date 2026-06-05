import clsx from "clsx";
import type { ReactNode } from "react";
import {
  korakuAppPageMaxWidth,
  type KorakuAppPageWidth,
} from "@/lib/koraku-ui";

export function KorakuAppPage({
  children,
  maxWidth = "3xl",
  density = "default",
  className,
}: {
  children: ReactNode;
  maxWidth?: KorakuAppPageWidth;
  density?: "default" | "compact";
  className?: string;
}) {
  return (
    <main
      className={clsx(
        "min-h-0 flex-1 overflow-y-auto bg-white",
        density === "compact" ? "px-4 py-4 sm:px-6 sm:py-5" : "px-4 py-8 sm:px-6 sm:py-10",
        className,
      )}
    >
      <div className={clsx("mx-auto", korakuAppPageMaxWidth[maxWidth])}>{children}</div>
    </main>
  );
}
