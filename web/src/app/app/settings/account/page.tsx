"use client";

import { KorakuAppPage } from "@/components/KorakuAppPage";
import { KorakuPageHeader } from "@/components/KorakuPageHeader";
import { SettingsAccountSection } from "@/components/SettingsAccountSection";

export default function SettingsAccountPage() {
  return (
    <KorakuAppPage maxWidth="3xl">
      <KorakuPageHeader
        eyebrow="Settings"
        title="Account & data"
        description="Export your data, delete app rows, and review privacy policies."
      />
      <div className="mt-8">
        <SettingsAccountSection />
      </div>
    </KorakuAppPage>
  );
}
