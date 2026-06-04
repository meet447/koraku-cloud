/**
 * Allow only safe link targets in assistant/workspace markdown.
 * Blocks javascript:, data:, and protocol-relative URLs.
 */
export function safeMarkdownHref(href: string | undefined): string | undefined {
  const raw = (href ?? "").trim();
  if (!raw) {
    return undefined;
  }
  if (raw.startsWith("#")) {
    return raw;
  }
  if (raw.startsWith("/") && !raw.startsWith("//")) {
    return raw;
  }
  const lower = raw.toLowerCase();
  if (
    lower.startsWith("javascript:") ||
    lower.startsWith("data:") ||
    lower.startsWith("vbscript:") ||
    lower.startsWith("//")
  ) {
    return undefined;
  }
  try {
    const url = new URL(raw);
    if (url.protocol === "http:" || url.protocol === "https:" || url.protocol === "mailto:") {
      return raw;
    }
  } catch {
    return undefined;
  }
  return undefined;
}
