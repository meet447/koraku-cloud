import DOMPurify from "isomorphic-dompurify";

/** Strip scripts, event handlers, and other active content from untrusted HTML. */
export function sanitizeHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
  });
}
