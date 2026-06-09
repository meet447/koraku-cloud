import type { PersonalizationPayload } from "@/lib/koraku-personalization";
import {
  buildMemoryFromSections,
  parseMemorySections,
  PROFILE_SECTION_HEADER,
  type ProfileLinkSummaryField,
} from "@/lib/personalization-memory";
import {
  collectProfileLinks,
  defaultLabelForLinkKind,
  emptyProfileLinkFormState,
  profileLinksToFormState,
  type ProfileLinkFormState,
} from "@/lib/profile-links";

const ONBOARDING_DONE_KEY = "koraku_onboarding_done";
const ONBOARDING_DRAFT_KEY = "koraku_onboarding_draft";
export const STARTER_PROMPTS_KEY = "koraku_starter_prompts";

export const ONBOARDING_STEP_IDS = [
  "name",
  "about",
  "agent-name",
  "preferences",
  "persona",
  "connections",
] as const;

export type OnboardingStepId = (typeof ONBOARDING_STEP_IDS)[number];

export type OnboardingFormData = {
  userName: string;
  about: string;
  additionalInfo: string;
  helpWith: string[];
  profileLinksForm: ProfileLinkFormState;
  linkSummaries: ProfileLinkSummaryField[];
  /** True after Describe yourself was generated; shows read-only profile until Start over. */
  aboutProfileReady: boolean;
  agentName: string;
  preferences: string;
  persona: string;
};

export const ONBOARDING_HELP_OPTIONS = [
  "Remember my preferences and context",
  "Organize notes, plans, and decisions",
  "Research and summarize topics for me",
  "Automate recurring personal admin",
  "Help me follow through on tasks",
  "Draft messages and follow-ups",
] as const;

export const ONBOARDING_PREFERENCE_SUGGESTIONS = [
  "Concise answers with clear next steps",
  "Ask before sending email or changing calendars",
  "Cite sources when researching",
  "Prefer bullet lists over long paragraphs",
] as const;

export const ONBOARDING_PERSONA_SUGGESTIONS = [
  "Warm mentor — practical, no fluff",
  "Direct operator — short and decisive",
  "Thoughtful analyst — careful and structured",
  "Friendly coach — encouraging and clear",
] as const;

/** Popular integrations offered on the connections step (Composio toolkit slugs). */
export const ONBOARDING_CONNECTION_SLUGS = [
  "GMAIL",
  "GOOGLECALENDAR",
  "GOOGLEDRIVE",
  "SLACK",
  "NOTION",
  "LINEAR",
  "GITHUB",
  "HUBSPOT",
] as const;

export const ONBOARDING_STEPS: ReadonlyArray<{
  id: OnboardingStepId;
  title: string;
  description: string;
}> = [
  {
    id: "name",
    title: "What should we call you?",
    description: "Your name is saved to memory so agents greet you correctly.",
  },
  {
    id: "about",
    title: "What do you do?",
    description:
      "Add links and anything else we should know — Koraku drafts your About in your voice when you continue.",
  },
  {
    id: "agent-name",
    title: "Name your agent",
    description: "This is how your companion appears in chat and iMessage.",
  },
  {
    id: "preferences",
    title: "Agent preferences",
    description: "Standing instructions injected into every conversation (saved as Memory).",
  },
  {
    id: "persona",
    title: "Agent persona",
    description: "Tone and style layered on Koraku behavior (saved as Soul).",
  },
  {
    id: "connections",
    title: "Connect your apps",
    description: "Link tools now or skip — you can always add more under Connections.",
  },
];

export const defaultOnboardingFormData = (): OnboardingFormData => ({
  userName: "",
  about: "",
  additionalInfo: "",
  helpWith: [ONBOARDING_HELP_OPTIONS[0]],
  profileLinksForm: emptyProfileLinkFormState(),
  linkSummaries: [],
  aboutProfileReady: false,
  agentName: "Koraku",
  preferences: ONBOARDING_PREFERENCE_SUGGESTIONS[0],
  persona: ONBOARDING_PERSONA_SUGGESTIONS[0],
});

export function isOnboardingComplete(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(ONBOARDING_DONE_KEY) === "1";
  } catch {
    return false;
  }
}

export const ONBOARDING_COMPLETE_EVENT = "koraku-onboarding-complete";
export const ONBOARDING_RESET_EVENT = "koraku-onboarding-reset";

export function markOnboardingComplete(): void {
  try {
    window.localStorage.setItem(ONBOARDING_DONE_KEY, "1");
    window.sessionStorage.removeItem(ONBOARDING_DRAFT_KEY);
    window.dispatchEvent(new Event(ONBOARDING_COMPLETE_EVENT));
  } catch {
    /* ignore */
  }
}

/** Clears client onboarding flags so the next signed-in user is not gated by a prior account. */
export function clearOnboardingClientState(): void {
  try {
    window.localStorage.removeItem(ONBOARDING_DONE_KEY);
    window.localStorage.removeItem(STARTER_PROMPTS_KEY);
    window.sessionStorage.removeItem(ONBOARDING_DRAFT_KEY);
  } catch {
    /* ignore */
  }
}

/** Clear local onboarding flags and notify the app shell to re-check server profile. */
export function resetOnboardingClientState(): void {
  clearOnboardingClientState();
  try {
    window.dispatchEvent(new Event(ONBOARDING_RESET_EVENT));
  } catch {
    /* ignore */
  }
}

/** True when saved personalization already contains a finished onboarding profile. */
export function hasPersonalizationOnboardingProfile(memory: string): boolean {
  const text = memory.trim();
  if (!text.includes(PROFILE_SECTION_HEADER)) return false;
  const { profile } = parseMemorySections(text);
  return Boolean(profile.userName.trim() && profile.about.trim());
}

export type OnboardingDraft = OnboardingFormData & { stepIndex: number };

export function loadOnboardingDraft(): OnboardingDraft | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(ONBOARDING_DRAFT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<OnboardingDraft>;
    const base = defaultOnboardingFormData();
    const stepIndex =
      typeof parsed.stepIndex === "number"
        ? Math.min(Math.max(0, parsed.stepIndex), ONBOARDING_STEP_IDS.length - 1)
        : 0;
    return {
      userName: typeof parsed.userName === "string" ? parsed.userName : base.userName,
      about: typeof parsed.about === "string" ? parsed.about : base.about,
      additionalInfo:
        typeof parsed.additionalInfo === "string" ? parsed.additionalInfo : base.additionalInfo,
      helpWith: Array.isArray(parsed.helpWith) ? parsed.helpWith.map(String) : base.helpWith,
      profileLinksForm:
        parsed.profileLinksForm && typeof parsed.profileLinksForm === "object"
          ? {
              linkedinUrl:
                typeof (parsed.profileLinksForm as ProfileLinkFormState).linkedinUrl === "string"
                  ? (parsed.profileLinksForm as ProfileLinkFormState).linkedinUrl
                  : base.profileLinksForm.linkedinUrl,
              xUrl:
                typeof (parsed.profileLinksForm as ProfileLinkFormState).xUrl === "string"
                  ? (parsed.profileLinksForm as ProfileLinkFormState).xUrl
                  : base.profileLinksForm.xUrl,
              customLinks: Array.isArray((parsed.profileLinksForm as ProfileLinkFormState).customLinks)
                ? (parsed.profileLinksForm as ProfileLinkFormState).customLinks
                    .slice(0, 3)
                    .map((row) => ({
                      label: typeof row?.label === "string" ? row.label : "Link",
                      url: typeof row?.url === "string" ? row.url : "",
                    }))
                : base.profileLinksForm.customLinks,
            }
          : base.profileLinksForm,
      aboutProfileReady:
        typeof parsed.aboutProfileReady === "boolean"
          ? parsed.aboutProfileReady
          : Boolean(typeof parsed.about === "string" && parsed.about.trim()),
      linkSummaries: Array.isArray(parsed.linkSummaries)
        ? parsed.linkSummaries
            .map((row) => {
              if (!row || typeof row !== "object") return null;
              const label = typeof row.label === "string" ? row.label : "";
              const summary = typeof row.summary === "string" ? row.summary : "";
              return label && summary ? { label, summary } : null;
            })
            .filter((row): row is ProfileLinkSummaryField => row !== null)
        : base.linkSummaries,
      agentName: typeof parsed.agentName === "string" ? parsed.agentName : base.agentName,
      preferences: typeof parsed.preferences === "string" ? parsed.preferences : base.preferences,
      persona: typeof parsed.persona === "string" ? parsed.persona : base.persona,
      stepIndex,
    };
  } catch {
    return null;
  }
}

export function saveOnboardingDraft(data: OnboardingFormData, stepIndex: number): void {
  try {
    window.sessionStorage.setItem(
      ONBOARDING_DRAFT_KEY,
      JSON.stringify({ ...data, stepIndex } satisfies OnboardingDraft),
    );
  } catch {
    /* ignore */
  }
}

export function buildPersonalizationFromOnboarding(
  data: OnboardingFormData,
): PersonalizationPayload {
  return {
    agent_name: data.agentName.trim() || "Koraku",
    memory: buildMemoryFromSections(
      {
        userName: data.userName,
        about: data.about,
        helpWith: data.helpWith,
        profileLinks: collectProfileLinks(data.profileLinksForm),
        linkSummaries: data.linkSummaries,
      },
      data.preferences,
    ),
    soul: data.persona.trim(),
  };
}

export function buildStarterPrompts(data: OnboardingFormData): string[] {
  const prompts = [
    data.userName.trim()
      ? `Hi — I'm ${data.userName.trim()}. What do you already know about me from my profile?`
      : "What do you already know about me from my profile?",
  ];
  if (data.helpWith.length) {
    prompts.push(`Remember that I want Koraku to help with: ${data.helpWith.join(", ")}`);
  }
  if (data.about.trim()) {
    prompts.push(`Given that I ${data.about.trim().slice(0, 200)}, suggest three useful starter workflows.`);
  } else {
    prompts.push("Suggest three useful starter workflows for me.");
  }
  return prompts;
}

export function hasAboutGenerationContext(data: OnboardingFormData): boolean {
  return (
    collectProfileLinks(data.profileLinksForm).length > 0 ||
    Boolean(data.additionalInfo.trim()) ||
    data.helpWith.length > 0
  );
}

export function isAboutProfileReady(data: OnboardingFormData): boolean {
  return data.aboutProfileReady && Boolean(data.about.trim());
}

export function shouldAutoGenerateAboutOnNext(data: OnboardingFormData): boolean {
  return !isAboutProfileReady(data) && hasAboutGenerationContext(data);
}

export function resetAboutProfileFields(): Pick<
  OnboardingFormData,
  "about" | "linkSummaries" | "aboutProfileReady"
> {
  return {
    about: "",
    linkSummaries: [],
    aboutProfileReady: false,
  };
}

export function pendingProfileLinksForDisplay(data: OnboardingFormData) {
  return collectProfileLinks(data.profileLinksForm).map((link) => ({
    label: defaultLabelForLinkKind(link.kind, link.label),
    url: link.url,
  }));
}

export function linkSummariesFromResults(
  linkResults: Array<{ label: string; summary: string | null }>,
): ProfileLinkSummaryField[] {
  return linkResults
    .map((row) => {
      const text = row.summary?.trim();
      return text ? { label: row.label, summary: text } : null;
    })
    .filter((row): row is ProfileLinkSummaryField => row !== null);
}

export function validateOnboardingStep(
  stepId: OnboardingStepId,
  data: OnboardingFormData,
): string | null {
  switch (stepId) {
    case "name":
      if (!data.userName.trim()) return "Please enter your name.";
      return null;
    case "about": {
      if (isAboutProfileReady(data)) {
        if (data.helpWith.length === 0) return "Pick at least one way Koraku should help.";
        return null;
      }
      if (!hasAboutGenerationContext(data)) {
        return "Add links, additional context, or pick how Koraku should help.";
      }
      if (data.helpWith.length === 0) return "Pick at least one way Koraku should help.";
      return null;
    }
    case "agent-name":
      if (!data.agentName.trim()) return "Give your agent a name.";
      return null;
    case "preferences":
    case "persona":
    case "connections":
      return null;
    default:
      return null;
  }
}
