import { describe, expect, it } from "vitest";
import {
  collectProfileLinks,
  emptyProfileLinkFormState,
  normalizeProfileUrl,
  profileLinksToFormState,
} from "@/lib/profile-links";

describe("profile-links", () => {
  it("normalizes bare domains to https", () => {
    expect(normalizeProfileUrl("example.com/about")).toBe("https://example.com/about");
  });

  it("collects linkedin, x, and custom links with dedupe", () => {
    const links = collectProfileLinks({
      linkedinUrl: "https://linkedin.com/in/alex",
      xUrl: "https://twitter.com/alex",
      customLinks: [
        { label: "Portfolio", url: "https://alex.dev" },
        { label: "Blog", url: "https://alex.dev" },
      ],
    });
    expect(links).toHaveLength(3);
    expect(links[1]?.url).toContain("x.com");
  });

  it("round-trips form state", () => {
    const form = {
      ...emptyProfileLinkFormState(),
      linkedinUrl: "https://linkedin.com/in/alex",
      customLinks: [{ label: "Site", url: "https://alex.dev" }],
    };
    const links = collectProfileLinks(form);
    const restored = profileLinksToFormState(links);
    expect(restored.linkedinUrl).toBe(form.linkedinUrl);
    expect(restored.customLinks[0]?.url).toBe("https://alex.dev/");
  });
});
