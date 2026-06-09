"use client";

import { SettingsPageShell } from "@/components/SettingsPageShell";
import { SkillsSection } from "@/components/SkillsSection";

export default function SettingsSkillsPage() {
  return (
    <SettingsPageShell
      title="Skills"
      description="Custom playbooks your agent can follow. Bundled platform skills still apply when you have none enabled here."
    >
      <SkillsSection />
    </SettingsPageShell>
  );
}
