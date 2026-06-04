"use client";

import { SettingsPageShell } from "@/components/SettingsPageShell";
import { SettingsAccountSection } from "@/components/SettingsAccountSection";

export default function SettingsAccountPage() {
  return (
    <SettingsPageShell
      title="Account & data"
      description="Export your data, delete app rows, and review privacy policies."
    >
      <SettingsAccountSection hideIntro />
    </SettingsPageShell>
  );
}
