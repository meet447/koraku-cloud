import { CoreFeatures } from "@/components/landing/CoreFeatures";
import { Hero } from "@/components/landing/Hero";
import { KorakuFooter } from "@/components/landing/KorakuFooter";
import { landingFontClassName } from "@/components/landing/LandingShell";
import { LogoMarquee } from "@/components/landing/LogoMarquee";
import { ModernHeroSection } from "@/components/landing/ModernHeroSection";
import { cn } from "@/lib/cn";

export function LandingPage() {
  return (
    <main className={cn(landingFontClassName(), "min-h-screen overflow-x-hidden bg-landing-stone")}>
      <Hero />
      <CoreFeatures />
      <section className="bg-landing-shell px-5 py-16 md:px-8 md:py-20">
        <div className="mx-auto w-full max-w-[1400px]">
          <ModernHeroSection />
          <LogoMarquee />
        </div>
      </section>
      <KorakuFooter />
    </main>
  );
}
