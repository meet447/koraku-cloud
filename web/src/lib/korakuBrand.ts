/**
 * User-facing product copy. Avoid naming third-party infrastructure or API vendors
 * in the UI — use Koraku-branded language instead.
 */

/** Display name for an LLM provider id from the API (composer model picker). */
export function modelProviderDisplayName(providerId: string, apiLabel?: string): string {
  const id = providerId.toLowerCase();
  const map: Record<string, string> = {
    fireworks: "Koraku",
    anthropic: "Advanced",
    openai: "Standard",
    custom: "Custom",
    groq: "Fast",
    together: "Hosted",
  };
  if (map[id]) return map[id];
  const fromApi = (apiLabel || "").trim();
  if (fromApi && !looksLikeVendorName(fromApi)) return fromApi;
  return "Model";
}

function looksLikeVendorName(label: string): boolean {
  const lower = label.toLowerCase();
  const vendors = [
    "fireworks",
    "anthropic",
    "openai",
    "supabase",
    "composio",
    "blaxel",
    "supermemory",
    "exa",
    "firecrawl",
  ];
  return vendors.some((v) => lower.includes(v));
}

export const KORAKU_COPY = {
  memoryIntro:
    "Facts Koraku learns automatically from your conversations. Name, tone, and standing preferences live in Personalization.",
  workspaceEmptyHint:
    "Your Koraku workspace folder appears here after the first reply streams.",
  workspaceTitle: "Workspace",
  connectedAppsWorker: "Connected apps",
  integrationsDisabled:
    "Connections are not enabled for this workspace yet. You can still browse options below; linking will work once setup is complete.",
  authNotConfigured:
    "Sign-in is not configured on this server. Ask your administrator to enable Google or GitHub sign-in.",
  localDevNoAuth:
    "Running locally without sign-in?",
  dataStoredInKoraku:
    "stored in your Koraku account",
  deleteDataNote:
    "This removes chat history, personalization, automations, and automation runs stored in Koraku. Long-term learned memory may be retained separately and is not cleared by this action. It does not delete your sign-in account or data held by external services you connected.",
  privacyProcessing:
    "Prompts, messages, and tool context are processed by Koraku’s language models. Connected app actions and cloud workspace files use Koraku’s secure execution environment when enabled.",
  privacyStorage:
    "Koraku stores chat history, personalization, automation definitions, and automation run history in your account. Active chat sessions and in-progress runs may also be held temporarily on Koraku servers.",
  exportNote:
    "This export includes Koraku data available to your account. Data held by connected services or model providers may be governed by their own policies.",
  deleteApiNote:
    "Koraku app data was deleted. Removing your sign-in account or disconnecting linked apps may require additional steps.",
  setupLlm:
    "No language model is configured yet. Add your model API key in the server environment, then restart the API.",
  externalIntro:
    "Text or send voice notes from iMessage or SMS after you verify your number. Linked threads appear in chat like any other conversation.",
  externalNotConfigured:
    "Phone messaging is not enabled on this server yet. Ask your administrator to complete messaging setup.",
  externalLinkedHint:
    "Open your linked thread in Koraku to continue the conversation on the web.",
} as const;
