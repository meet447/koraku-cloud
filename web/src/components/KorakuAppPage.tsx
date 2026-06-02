import clsx from "clsx";
import type { ReactNode } from "react";
import {
  korakuAppPageMaxWidth,
  type KorakuAppPageWidth,
} from "@/lib/koraku-ui";

export function KorakuAppPage({
  children,
  maxWidth = "3xl",
  className,
}: {
  children: ReactNode;
  maxWidth?: KorakuAppPageWidth;
  className?: string;
}) {
  return (
    <main
      className={clsx(
        "min-h-0 flex-1 overflow-y-auto bg-white px-6 py-10",
        className,
      )}
    >
      <div className={clsx("mx-auto", korakuAppPageMaxWidth[maxWidth])}>{children}</div>
    </main>
  );
}
