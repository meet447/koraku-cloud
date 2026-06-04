"use client";

import { KorakuAppPage } from "@/components/KorakuAppPage";
import { KorakuPageHeader } from "@/components/KorakuPageHeader";
import { UserProfileSection } from "@/components/UserProfileSection";

export default function SettingsProfilePage() {
  return (
    <KorakuAppPage maxWidth="3xl">
      <KorakuPageHeader
        eyebrow="Settings"
        title="Personal info"
        description="Your name, background, and how you want Koraku to help."
      />
      <div className="mt-8">
        <UserProfileSection />
      </div>
    </KorakuAppPage>
  );
}
