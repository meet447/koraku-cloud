import type { Metadata } from "next";
import { appPageMetadata } from "@/lib/app-page-metadata";
import { OnboardingWizard } from "@/components/onboarding/OnboardingWizard";

export const metadata: Metadata = appPageMetadata(
  "Onboarding",
  "Set up your Koraku profile and preferences.",
);

export default function OnboardingPage() {
  return <OnboardingWizard />;
}
