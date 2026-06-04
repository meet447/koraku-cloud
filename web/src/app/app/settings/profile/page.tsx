"use client";

import { SettingsPageShell } from "@/components/SettingsPageShell";
import { UserProfileSection } from "@/components/UserProfileSection";

export default function SettingsProfilePage() {
  return (
    <SettingsPageShell
      title="Personal info"
      description="Your name, background, and how you want Koraku to help."
    >
      <UserProfileSection hideIntro />
    </SettingsPageShell>
  );
}
