"use client";

import { KorakuAppPage } from "@/components/KorakuAppPage";
import { KorakuPageHeader } from "@/components/KorakuPageHeader";
import { PersonalizationSection } from "@/components/PersonalizationSection";

export default function SettingsAgentPage() {
  return (
    <KorakuAppPage maxWidth="3xl">
      <KorakuPageHeader
        eyebrow="Settings"
        title="Agent info"
        description="How your agent shows up in chat: name, preferences, and persona."
      />
      <div className="mt-8">
        <PersonalizationSection />
      </div>
    </KorakuAppPage>
  );
}
