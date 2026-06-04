import { describe, expect, it } from "vitest";
import { messagesAppUrl } from "./messages-app-url";

describe("messagesAppUrl", () => {
  it("builds sms URI for E.164", () => {
    expect(messagesAppUrl("+1 (415) 555-1234")).toBe("sms:+14155551234");
  });

  it("returns empty for blank input", () => {
    expect(messagesAppUrl("  ")).toBe("");
  });
});
