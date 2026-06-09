import type { PersonalizationPayload } from "@/lib/koraku-personalization";
import {
  buildMemoryFromSections,
  parseMemorySections,
  PROFILE_SECTION_HEADER,
} from "@/lib/personalization-memory";

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
  helpWith: string[];
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
    description: "A short intro helps Koraku tailor research, planning, and automations.",
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
  helpWith: [ONBOARDING_HELP_OPTIONS[0]],
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
      helpWith: Array.isArray(parsed.helpWith) ? parsed.helpWith.map(String) : base.helpWith,
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

export function validateOnboardingStep(
  stepId: OnboardingStepId,
  data: OnboardingFormData,
): string | null {
  switch (stepId) {
    case "name":
      if (!data.userName.trim()) return "Please enter your name.";
      return null;
    case "about":
      if (!data.about.trim()) return "Tell us a little about what you do.";
      if (data.about.trim().length < 8) return "Add at least a short sentence.";
      if (data.helpWith.length === 0) return "Pick at least one way Koraku should help.";
      return null;
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
