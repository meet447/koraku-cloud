import { ChaptersSection } from "@/components/landing/ChaptersSection";
import { HeroSection } from "@/components/landing/HeroSection";
import { landingFontClassName } from "@/components/landing/LandingShell";
import { LeftRail } from "@/components/landing/LeftRail";
import { ModelsSection } from "@/components/landing/ModelsSection";
import { PixelFooter } from "@/components/landing/PixelFooter";
import { ToolsGrid } from "@/components/landing/ToolsGrid";
import { TopNav } from "@/components/landing/TopNav";
import { TrustStrip } from "@/components/landing/TrustStrip";
import { cn } from "@/lib/cn";

export function LandingPage() {
  return (
    <div className={cn(landingFontClassName(), "h-screen overflow-hidden bg-[#f8f8f7] text-[#282522] lg:grid lg:grid-cols-[210px_1fr]")}>
      <LeftRail />
      <main className="h-screen min-w-0 overflow-y-auto overflow-x-hidden">
        <TopNav />
        <HeroSection />
        <ChaptersSection />
        <ModelsSection />
        <ToolsGrid />
        <TrustStrip />
        <PixelFooter />
      </main>
    </div>
  );
}
