import { CoreFeatures } from "@/components/landing/CoreFeatures";
import { Hero } from "@/components/landing/Hero";
import { KorakuFooter } from "@/components/landing/KorakuFooter";
import { ModernLandingSection } from "@/components/landing/ModernLandingSection";
import { LANDING } from "@/lib/landing-theme";

export default function LandingPage() {
  return (
    <main className="landing-page min-h-screen" style={{ backgroundColor: LANDING.bg }}>
      <Hero />
      <CoreFeatures />
      <ModernLandingSection />
      <KorakuFooter />
    </main>
  );
}
