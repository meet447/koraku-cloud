export type ProfileLinkKind = "linkedin" | "x" | "custom";

export type ProfileLink = {
  kind: ProfileLinkKind;
  url: string;
  label?: string;
};

export type CustomProfileLink = {
  label: string;
  url: string;
};

export type ProfileLinkFormState = {
  linkedinUrl: string;
  xUrl: string;
  customLinks: CustomProfileLink[];
};

export type ProfileLinkResult = {
  kind: ProfileLinkKind;
  url: string;
  label: string;
  status: "ok" | "failed" | "skipped";
  summary: string | null;
  error: string | null;
};

export const MAX_PROFILE_LINKS = 5;
export const MAX_CUSTOM_PROFILE_LINKS = 3;

export const emptyProfileLinkFormState = (): ProfileLinkFormState => ({
  linkedinUrl: "",
  xUrl: "",
  customLinks: [],
});

export function normalizeProfileUrl(raw: string): string | null {
  const text = raw.trim();
  if (!text) return null;
  const withScheme = /^https?:\/\//i.test(text) ? text : `https://${text}`;
  try {
    const parsed = new URL(withScheme);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return null;
    const host = parsed.hostname.toLowerCase();
    if (!host || host === "localhost" || host.endsWith(".localhost")) return null;
    return parsed.toString();
  } catch {
    return null;
  }
}

export function normalizeXUrl(raw: string): string | null {
  const normalized = normalizeProfileUrl(raw);
  if (!normalized) return null;
  try {
    const parsed = new URL(normalized);
    if (parsed.hostname.toLowerCase() === "twitter.com") {
      parsed.hostname = "x.com";
      return parsed.toString();
    }
    return parsed.toString();
  } catch {
    return null;
  }
}

export function collectProfileLinks(form: ProfileLinkFormState): ProfileLink[] {
  const out: ProfileLink[] = [];
  const seen = new Set<string>();

  const push = (link: ProfileLink) => {
    const url =
      link.kind === "x" ? normalizeXUrl(link.url) : normalizeProfileUrl(link.url);
    if (!url || seen.has(url)) return;
    seen.add(url);
    out.push({ ...link, url });
  };

  if (form.linkedinUrl.trim()) {
    push({ kind: "linkedin", url: form.linkedinUrl.trim() });
  }
  if (form.xUrl.trim()) {
    push({ kind: "x", url: form.xUrl.trim() });
  }
  for (const row of form.customLinks) {
    const url = row.url.trim();
    if (!url) continue;
    push({
      kind: "custom",
      url,
      label: row.label.trim() || "Link",
    });
    if (out.length >= MAX_PROFILE_LINKS) break;
  }

  return out.slice(0, MAX_PROFILE_LINKS);
}

export function profileLinksToFormState(links: ProfileLink[]): ProfileLinkFormState {
  const state = emptyProfileLinkFormState();
  const customs: CustomProfileLink[] = [];

  for (const link of links) {
    if (link.kind === "linkedin" && !state.linkedinUrl) {
      state.linkedinUrl = link.url;
      continue;
    }
    if (link.kind === "x" && !state.xUrl) {
      state.xUrl = link.url;
      continue;
    }
    if (link.kind === "custom" && customs.length < MAX_CUSTOM_PROFILE_LINKS) {
      customs.push({ label: link.label?.trim() || "Link", url: link.url });
    }
  }

  state.customLinks = customs;
  return state;
}

export function defaultLabelForLinkKind(kind: ProfileLinkKind, label?: string): string {
  if (kind === "linkedin") return "LinkedIn";
  if (kind === "x") return "X";
  return label?.trim() || "Link";
}
