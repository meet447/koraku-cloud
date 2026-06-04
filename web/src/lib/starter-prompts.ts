import { STARTER_PROMPTS_KEY } from "@/lib/onboarding";

const DEFAULT_STARTER_PROMPTS = [
  "Remember how I like to work and ask three setup questions.",
  "Create a second-brain note for my current priorities.",
  "Suggest one useful daily automation I can safely try.",
] as const;

export function readStarterPrompts(): string[] {
  if (typeof window === "undefined") {
    return [...DEFAULT_STARTER_PROMPTS];
  }
  try {
    const raw = window.localStorage.getItem(STARTER_PROMPTS_KEY);
    if (!raw) return [...DEFAULT_STARTER_PROMPTS];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((p): p is string => typeof p === "string").slice(0, 3);
  } catch {
    return [];
  }
}
