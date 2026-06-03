export const navItems = [
  { label: "How it works", href: "#how-it-works" },
  { label: "Use cases", href: "#use-cases" },
  { label: "Features", href: "#features" },
  { label: "Automations", href: "#automations" },
  { label: "Models", href: "#models" },
  { label: "Integrations", href: "#integrations" },
  { label: "Trust", href: "#trust" },
] as const;

export const howItWorksSteps = [
  {
    step: "01",
    title: "Connect",
    description:
      "Link Gmail, Notion, Linear, and the rest once in Settings. Koraku pulls live context from the apps you already use.",
  },
  {
    step: "02",
    title: "Instruct",
    description:
      "Describe outcomes in plain language. Agents follow your personalization and memory on every run — no scripts required.",
  },
  {
    step: "03",
    title: "Review & run",
    description:
      "Drafts land in your cloud workspace. Koraku asks before sending email, posting to chat, or changing records in connected apps.",
  },
] as const;

export type UseCase = {
  tag: string;
  title: string;
  outcome: string;
  bullets: readonly string[];
};

export const useCases: readonly UseCase[] = [
  {
    tag: "Use case 1",
    title: "Daily brief",
    outcome: "Start the day with one agent run across calendar, inbox, and notes.",
    bullets: [
      "Pull today’s meetings and conflicts",
      "Flag urgent threads and follow-ups",
      "Surface open tasks in your workspace",
    ],
  },
  {
    tag: "Use case 2",
    title: "Research desk",
    outcome: "Turn a question into sourced notes and files you can share.",
    bullets: [
      "Search connected docs and drives",
      "Summarize with clear takeaways",
      "Save outputs to your workspace library",
    ],
  },
  {
    tag: "Use case 3",
    title: "Follow-up engine",
    outcome: "Draft replies and updates without sending until you approve.",
    bullets: [
      "Propose email and chat drafts",
      "Sync task status to Linear or Asana",
      "Log decisions back to memory",
    ],
  },
  {
    tag: "Use case 4",
    title: "Second brain",
    outcome: "Preferences and facts carry into every new chat.",
    bullets: [
      "Learn your tone and goals over time",
      "Recall past decisions automatically",
      "Keep agent profile in sync everywhere",
    ],
  },
] as const;

export const featureDescriptions: Record<string, string> = {
  "Smart Agent Instructions":
    "Natural-language rules agents follow every run — who to notify, what to create, and when to pause for your approval.",
  "Connected Apps":
    "OAuth connections to your stack. Context stays in your Koraku account instead of scattered across one-off chats.",
  "Agent Workspace Library":
    "A cloud folder for drafts, exports, and agent-created files — searchable from chat whenever you need them.",
  "Learned Memory":
    "Koraku remembers facts from conversations so you do not re-explain preferences each session.",
  "iMessage and Voice Notes":
    "Message Koraku from your phone. Threads and voice notes sync to the web app like any other conversation.",
  "Personalization Layer":
    "Name, tone, and persona injected into every agent so behavior stays consistent across chat and automations.",
};

export const automationCards = [
  {
    title: "Scheduled runs",
    description:
      "Morning briefs, weekly digests, and inbox triage on a schedule — the same agents and rules you use in chat.",
  },
  {
    title: "Approval gates",
    description:
      "High-impact actions need your OK in the app before anything is sent or changed in a connected tool.",
  },
  {
    title: "Run history",
    description:
      "See what ran, what changed, and open results in your workspace without digging through old threads.",
  },
] as const;

export const modelUseCases = [
  {
    label: "Fast triage",
    detail: "Quick summaries, inbox sorting, and short replies when you need answers in seconds.",
  },
  {
    label: "Deep research",
    detail: "Longer reasoning for multi-source notes, comparisons, and workspace-ready write-ups.",
  },
  {
    label: "Daily default",
    detail: "Balanced model for everyday chat — switch per message in the composer without leaving the thread.",
  },
] as const;

export const integrationCategories = [
  "Email",
  "Docs",
  "Dev",
  "CRM",
  "Chat",
] as const;

export const popularWorkflows = [
  "Gmail thread → Linear issue with summary",
  "Notion pages → weekly team digest in workspace",
  "Calendar + inbox → daily brief before standup",
  "HubSpot notes → follow-up draft for approval",
] as const;

/** 16 integrations shown on the landing page (from the ~40-tool curated catalog). */
export const integrationShowcase = [
  { name: "Gmail", toolkit: "GMAIL", iconSlug: "gmail", hex: "EA4335" },
  { name: "Google Drive", toolkit: "GOOGLEDRIVE", iconSlug: "googledrive", hex: "4285F4" },
  { name: "Google Docs", toolkit: "GOOGLEDOCS", iconSlug: "googledocs", hex: "4285F4" },
  { name: "Calendar", toolkit: "GOOGLECALENDAR", iconSlug: "googlecalendar", hex: "4285F4" },
  { name: "Trello", toolkit: "TRELLO", iconSlug: "trello", hex: "0052CC" },
  { name: "Notion", toolkit: "NOTION", iconSlug: "notion", hex: "000000" },
  { name: "GitHub", toolkit: "GITHUB", iconSlug: "github", hex: "181717" },
  { name: "Linear", toolkit: "LINEAR", iconSlug: "linear", hex: "5E6AD2" },
  { name: "Jira", toolkit: "JIRA", iconSlug: "jira", hex: "0052CC" },
  { name: "Airtable", toolkit: "AIRTABLE", iconSlug: "airtable", hex: "18BFFF" },
  { name: "Asana", toolkit: "ASANA", iconSlug: "asana", hex: "F06A6A" },
  { name: "Discord", toolkit: "DISCORD", iconSlug: "discord", hex: "5865F2" },
  { name: "Dropbox", toolkit: "DROPBOX", iconSlug: "dropbox", hex: "0061FF" },
  { name: "Zoom", toolkit: "ZOOM", iconSlug: "zoom", hex: "0B5CFF" },
  { name: "HubSpot", toolkit: "HUBSPOT", iconSlug: "hubspot", hex: "FF7A59" },
  { name: "iMessage", toolkit: "imessage", iconSlug: "imessage", hex: "34C759" },
] as const;

export const trustPoints = [
  {
    title: "Ask before acting",
    description:
      "Sending messages, sharing files, or updating external systems requires your confirmation in the app.",
  },
  {
    title: "Your Koraku account",
    description:
      "Chat history, personalization, automations, and workspace files live in your account — ready when you sign back in.",
  },
  {
    title: "Connected apps",
    description:
      "Third-party access uses standard OAuth. Connect or revoke tools anytime from Settings.",
  },
  {
    title: "Clear policies",
    description:
      "See how Koraku processes and stores data in our privacy policy — written for everyday use, not legalese alone.",
  },
] as const;
