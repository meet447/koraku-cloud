/** Known Composio toolkit slugs with brand hex colors for Simple Icons. */
const TOOLKIT_BRAND_ICONS: Record<string, { slug: string; hex: string }> = {
  GMAIL: { slug: "gmail", hex: "EA4335" },
  NOTION: { slug: "notion", hex: "000000" },
  GOOGLEDRIVE: { slug: "googledrive", hex: "4285F4" },
  SLACK: { slug: "slack", hex: "4A154B" },
  AIRTABLE: { slug: "airtable", hex: "18BFFF" },
  ASANA: { slug: "asana", hex: "F06A6A" },
  BOX: { slug: "box", hex: "0061D5" },
};

/** Simple Icons CDN URL for integration / toolkit logos. */
export function toolkitIconUrl(slug: string, hex?: string): string {
  const encoded = encodeURIComponent(slug);
  return hex
    ? `https://cdn.simpleicons.org/${encoded}/${hex.replace(/^#/, "")}`
    : `https://cdn.simpleicons.org/${encoded}`;
}

/** Icon URL for a Composio toolkit code (e.g. GMAIL, SLACK). */
export function automationToolkitIconUrl(toolkit: string): string {
  const key = toolkit.toUpperCase();
  const brand = TOOLKIT_BRAND_ICONS[key] ?? { slug: key.toLowerCase(), hex: "737373" };
  return toolkitIconUrl(brand.slug, brand.hex);
}
