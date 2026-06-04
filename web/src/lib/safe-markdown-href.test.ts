import { describe, expect, it } from "vitest";
import { safeMarkdownHref } from "./safe-markdown-href";

describe("safeMarkdownHref", () => {
  it("allows https and relative paths", () => {
    expect(safeMarkdownHref("https://example.com/x")).toBe("https://example.com/x");
    expect(safeMarkdownHref("/app/settings")).toBe("/app/settings");
    expect(safeMarkdownHref("#section")).toBe("#section");
  });

  it("blocks javascript and protocol-relative URLs", () => {
    expect(safeMarkdownHref("javascript:alert(1)")).toBeUndefined();
    expect(safeMarkdownHref("//evil.example")).toBeUndefined();
    expect(safeMarkdownHref("data:text/html,x")).toBeUndefined();
  });
});
