import { Inter, Outfit } from "next/font/google";
import { LogoMarquee } from "@/components/landing/LogoMarquee";
import { ModernHeroSection } from "@/components/landing/ModernHeroSection";
import { cn } from "@/lib/cn";

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-inter",
});

const outfit = Outfit({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
  variable: "--font-outfit",
});

/** Modern hero + logo marquee block (Inter/Outfit, #f9fafb shell). */
export function ModernLandingSection() {
  return (
    <section
      className={cn(
        inter.variable,
        outfit.variable,
        "bg-[#f9fafb] px-5 py-16 font-landing-sans md:px-8 md:py-20",
      )}
    >
      <div className="mx-auto w-full max-w-[1400px]">
        <ModernHeroSection />
        <LogoMarquee />
      </div>
    </section>
  );
}
