import clsx from "clsx";
import type { ReactNode } from "react";
import { KorakuAppPage } from "@/components/KorakuAppPage";
import { KorakuPageHeader } from "@/components/KorakuPageHeader";
import { korakuUi } from "@/lib/koraku-ui";

type SettingsPageShellProps = {
  title: string;
  description: ReactNode;
  action?: ReactNode;
  children: ReactNode;
};

/** Compact settings layout — wider content, tighter vertical rhythm. */
export function SettingsPageShell({
  title,
  description,
  action,
  children,
}: SettingsPageShellProps) {
  return (
    <KorakuAppPage maxWidth="4xl" density="compact">
      <KorakuPageHeader
        eyebrow="Settings"
        title={title}
        description={description}
        action={action}
        density="compact"
      />
      <div className={clsx("mt-4", korakuUi.settingsStack)}>{children}</div>
    </KorakuAppPage>
  );
}
