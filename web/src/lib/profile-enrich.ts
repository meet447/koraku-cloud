import { korakuFetchJson } from "@/lib/koraku-fetch";
import type { ProfileLink, ProfileLinkResult } from "@/lib/profile-links";

export type ProfileEnrichResponse = {
  about: string;
  link_results: ProfileLinkResult[];
};

export async function enrichProfileFromLinks(input: {
  userName?: string;
  existingAbout?: string;
  additionalInfo?: string;
  helpWith?: string[];
  links: ProfileLink[];
}): Promise<ProfileEnrichResponse> {
  return korakuFetchJson<ProfileEnrichResponse>("/koraku-api/api/profile/enrich", {
    method: "POST",
    json: {
      user_name: input.userName?.trim() || null,
      existing_about: input.existingAbout?.trim() || null,
      additional_info: input.additionalInfo?.trim() || null,
      help_with: input.helpWith?.map((item) => item.trim()).filter(Boolean) ?? [],
      links: input.links.map((link) => ({
        kind: link.kind,
        url: link.url,
        label: link.label?.trim() || null,
      })),
    },
  });
}
