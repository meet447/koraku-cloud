/** Split ``memory`` text into onboarding profile vs agent preferences. */

export const PROFILE_SECTION_HEADER = "## Onboarding profile";
const PREFERENCES_SECTION_HEADER = "## Preferences";

const PROFILE_SAFETY_LINE =
  "- When suggesting external actions, verify the target app/account and ask for confirmation before sending or changing data.";

export type ProfileLinkField = {
  kind: "linkedin" | "x" | "custom";
  url: string;
  label?: string;
};

export type ProfileLinkSummaryField = {
  label: string;
  summary: string;
};

export type UserProfileFields = {
  userName: string;
  about: string;
  helpWith: string[];
  profileLinks: ProfileLinkField[];
  linkSummaries: ProfileLinkSummaryField[];
};

export const emptyUserProfile = (): UserProfileFields => ({
  userName: "",
  about: "",
  helpWith: [],
  profileLinks: [],
  linkSummaries: [],
});

export function parseMemorySections(memory: string): {
  profile: UserProfileFields;
  preferences: string;
} {
  const text = memory.trim();
  if (!text) {
    return { profile: emptyUserProfile(), preferences: "" };
  }

  const prefIdx = text.indexOf(PREFERENCES_SECTION_HEADER);
  const hasProfile = text.includes(PROFILE_SECTION_HEADER);

  // Legacy memory: single block without onboarding sections → treat as preferences only.
  if (!hasProfile && prefIdx < 0) {
    return { profile: emptyUserProfile(), preferences: text };
  }

  const profileChunk = prefIdx >= 0 ? text.slice(0, prefIdx) : text;
  const prefChunk =
    prefIdx >= 0 ? text.slice(prefIdx + PREFERENCES_SECTION_HEADER.length) : "";

  return {
    profile: parseProfileChunk(profileChunk),
    preferences: prefChunk.trim(),
  };
}

function parseProfileChunk(chunk: string): UserProfileFields {
  let userName = "";
  let about = "";
  let helpWith: string[] = [];
  const profileLinks: ProfileLinkField[] = [];
  const linkSummaries: ProfileLinkSummaryField[] = [];
  let inLinkSummaries = false;

  for (const line of chunk.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (trimmed === "- Link summaries:") {
      inLinkSummaries = true;
      continue;
    }
    if (inLinkSummaries) {
      const match = trimmed.match(/^- (.+):\s*(.+)$/);
      if (match) {
        linkSummaries.push({ label: match[1].trim(), summary: match[2].trim() });
      }
      continue;
    }
    if (trimmed.startsWith("- User name:")) {
      userName = trimmed.slice("- User name:".length).trim();
    } else if (trimmed.startsWith("- About:")) {
      about = trimmed.slice("- About:".length).trim();
    } else if (trimmed.startsWith("- Koraku should help with:")) {
      helpWith = trimmed
        .slice("- Koraku should help with:".length)
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    } else if (trimmed.startsWith("- Public links:")) {
      const payload = trimmed.slice("- Public links:".length).trim();
      for (const part of payload.split(";")) {
        const piece = part.trim();
        if (!piece) continue;
        const idx = piece.indexOf(":");
        if (idx < 0) continue;
        const label = piece.slice(0, idx).trim();
        const url = piece.slice(idx + 1).trim();
        if (!url) continue;
        const lower = label.toLowerCase();
        const kind =
          lower === "linkedin" ? "linkedin" : lower === "x" ? "x" : ("custom" as const);
        profileLinks.push({
          kind,
          url,
          label: kind === "custom" ? label : undefined,
        });
      }
    }
  }

  return { userName, about, helpWith, profileLinks, linkSummaries };
}

function formatPublicLinks(links: ProfileLinkField[]): string {
  return links
    .map((link) => {
      const label =
        link.kind === "linkedin" ? "LinkedIn" : link.kind === "x" ? "X" : link.label?.trim() || "Link";
      return `${label}: ${link.url}`;
    })
    .join("; ");
}

export function buildMemoryFromSections(
  profile: UserProfileFields,
  preferences: string,
): string {
  const profileLines = [
    PROFILE_SECTION_HEADER,
    profile.userName.trim() ? `- User name: ${profile.userName.trim()}` : "",
    profile.about.trim() ? `- About: ${profile.about.trim()}` : "",
    profile.profileLinks.length
      ? `- Public links: ${formatPublicLinks(profile.profileLinks)}`
      : "",
    profile.linkSummaries.length ? "- Link summaries:" : "",
    ...profile.linkSummaries.map((row) => `- ${row.label}: ${row.summary}`),
    profile.helpWith.length
      ? `- Koraku should help with: ${profile.helpWith.join(", ")}`
      : "",
    PROFILE_SAFETY_LINE,
  ].filter(Boolean);

  const preferenceBody =
    preferences.trim() ||
    "Prefer concise answers with clear next steps. Ask before high-impact external actions.";

  return [...profileLines, "", PREFERENCES_SECTION_HEADER, preferenceBody].join("\n");
}
