import { ChaptersSection } from "@/components/landing/ChaptersSection";
import { HeroSection } from "@/components/landing/HeroSection";
import { landingFontClassName } from "@/components/landing/LandingShell";
import { LeftRail } from "@/components/landing/LeftRail";
import { ModelsSection } from "@/components/landing/ModelsSection";
import { PixelFooter } from "@/components/landing/PixelFooter";
import { ToolsGrid } from "@/components/landing/ToolsGrid";
import { TopNav } from "@/components/landing/TopNav";
import { cn } from "@/lib/cn";
import { LANDING_PAGE_BG } from "@/components/landing/landing-layout";

export function LandingPage() {
  return (
    <div className={cn(landingFontClassName(), LANDING_PAGE_BG, "h-screen overflow-hidden text-[#282522] lg:grid lg:grid-cols-[240px_1fr]")}>
      <LeftRail />
      <main
        data-landing-scroll
        className="h-screen min-w-0 overflow-y-auto overflow-x-hidden"
      >
        <TopNav />
        <HeroSection />
        <ChaptersSection />
        <ModelsSection />
        <ToolsGrid />
        <PixelFooter />
      </main>
    </div>
  );
}
