/**
 * Koraku landing palette — warm stone + orange accent (matches in-app design language).
 * Use these tokens everywhere on the landing page; avoid one-off hex values in components.
 */
export const LANDING = {
  /** Outer shell and bottom-right cutout fill */
  bg: "#f7f4ef",
  /** Primary headings and nav */
  text: "#1c1917",
  /** Body copy, hero subtitle */
  textMuted: "#57534e",
  /** Labels, tertiary links */
  textSoft: "#78716c",
  /** Orange accent — badges, icons, links */
  accent: "#c2410c",
  accentStrong: "#9a3412",
  accentHover: "#7c2d12",
  accentMuted: "#ea580c",
  accentSoft: "rgba(251, 146, 60, 0.1)",
  accentBorder: "rgba(251, 146, 60, 0.22)",
  accentIconBg: "rgba(254, 215, 170, 0.55)",
  /** Primary CTA fill */
  cta: "#1c1917",
  ctaHover: "#292524",
} as const;

export const LANDING_VIDEO_SRC =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260428_193507_4286c423-2fd9-4efd-92bd-91a939453fc1.mp4";

/** Tailwind class bundles for consistent landing typography */
export const landingText = {
  nav: "text-[#1c1917]",
  headline: "text-[#1c1917]",
  body: "text-[#57534e]",
  label: "text-[#78716c]",
  accent: "text-[#c2410c]",
  accentStrong: "text-[#9a3412]",
} as const;
