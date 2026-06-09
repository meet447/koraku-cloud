import { describe, expect, it } from "vitest";
import { buildMemoryFromSections, parseMemorySections } from "@/lib/personalization-memory";

describe("personalization-memory profile links", () => {
  it("builds and parses public links and summaries", () => {
    const memory = buildMemoryFromSections(
      {
        userName: "Alex",
        about: "Product lead building Koraku.",
        helpWith: ["Remember my preferences and context"],
        profileLinks: [
          { kind: "linkedin", url: "https://linkedin.com/in/alex" },
          { kind: "custom", url: "https://alex.dev", label: "Portfolio" },
        ],
        linkSummaries: [{ label: "Portfolio", summary: "Writes about product and AI." }],
      },
      "Be concise.",
    );

    const { profile, preferences } = parseMemorySections(memory);
    expect(profile.userName).toBe("Alex");
    expect(profile.profileLinks).toHaveLength(2);
    expect(profile.linkSummaries[0]?.summary).toContain("product");
    expect(preferences).toContain("Be concise.");
  });
});
