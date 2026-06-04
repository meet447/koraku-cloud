"use client";

import { SettingsPageShell } from "@/components/SettingsPageShell";
import { PersonalizationSection } from "@/components/PersonalizationSection";

export default function SettingsAgentPage() {
  return (
    <SettingsPageShell
      title="Agent info"
      description="How your agent shows up in chat: name, preferences, and persona."
    >
      <PersonalizationSection hideIntro />
    </SettingsPageShell>
  );
}
