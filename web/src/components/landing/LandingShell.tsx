import { Caveat, Cormorant_Garamond, DM_Sans, Inter, Outfit, Pixelify_Sans } from "next/font/google";
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

const dmSans = DM_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-dm-sans",
});

const caveat = Caveat({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  display: "swap",
  variable: "--font-caveat",
});

const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-cormorant",
});

const pixelify = Pixelify_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-pixelify",
});

export function landingFontClassName() {
  return cn(
    inter.variable,
    outfit.variable,
    dmSans.variable,
    caveat.variable,
    cormorant.variable,
    pixelify.variable,
    "font-landing-sans text-landing-body antialiased",
  );
}

export { inter, outfit, dmSans, caveat, cormorant, pixelify };
