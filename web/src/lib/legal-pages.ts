/** Public legal & support routes — single source for footer and cross-links. */

export const LEGAL_LAST_UPDATED = "June 3, 2026";

export const LEGAL_CONTACT = {
  support: "support@koraku.app",
  privacy: "privacy@koraku.app",
  security: "meet.sonawane2015@gmail.com",
} as const;

export const legalPages = [
  { slug: "privacy", label: "Privacy Policy", href: "/privacy", description: "How we collect, use, and protect your data." },
  { slug: "terms", label: "Terms of Service", href: "/terms", description: "Rules for using the Koraku service." },
  { slug: "security", label: "Security", href: "/security", description: "How we protect your account and connected apps." },
  { slug: "cookies", label: "Cookie Policy", href: "/cookies", description: "Cookies and similar technologies we use." },
  { slug: "contact", label: "Contact", href: "/contact", description: "Support, privacy requests, and security reports." },
] as const;

export type LegalPageSlug = (typeof legalPages)[number]["slug"];
