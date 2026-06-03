/** Split ``memory`` text into onboarding profile vs agent preferences. */

export const PROFILE_SECTION_HEADER = "## Onboarding profile";
export const PREFERENCES_SECTION_HEADER = "## Preferences";

export const PROFILE_SAFETY_LINE =
  "- When suggesting external actions, verify the target app/account and ask for confirmation before sending or changing data.";

export type UserProfileFields = {
  userName: string;
  about: string;
  helpWith: string[];
};

export const emptyUserProfile = (): UserProfileFields => ({
  userName: "",
  about: "",
  helpWith: [],
});

export function parseUserProfileFromMemory(memory: string): UserProfileFields {
  const { profile } = parseMemorySections(memory);
  return profile;
}

export function parsePreferencesFromMemory(memory: string): string {
  return parseMemorySections(memory).preferences;
}

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

  for (const line of chunk.split("\n")) {
    const trimmed = line.trim();
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
    }
  }

  return { userName, about, helpWith };
}

export function buildMemoryFromSections(
  profile: UserProfileFields,
  preferences: string,
): string {
  const profileLines = [
    PROFILE_SECTION_HEADER,
    profile.userName.trim() ? `- User name: ${profile.userName.trim()}` : "",
    profile.about.trim() ? `- About: ${profile.about.trim()}` : "",
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
