import { describe, expect, it } from "vitest";
import { sanitizeHtml } from "./sanitize-html";

describe("sanitizeHtml", () => {
  it("removes script tags and inline handlers", () => {
    const dirty =
      '<p>Hello</p><script>alert(1)</script><img src=x onerror="alert(1)">';
    const clean = sanitizeHtml(dirty);
    expect(clean).not.toContain("<script");
    expect(clean).not.toContain("onerror");
    expect(clean).toContain("Hello");
  });

  it("preserves basic formatting from doc conversion", () => {
    const html = "<p><strong>Title</strong></p><ul><li>One</li></ul>";
    expect(sanitizeHtml(html)).toBe(html);
  });
});
