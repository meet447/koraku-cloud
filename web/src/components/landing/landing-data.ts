export const navItems = [
  { label: "Use cases", href: "#how-to" },
  { label: "Models", href: "#models" },
  { label: "Integrations", href: "#integrations" },
  { label: "Safety", href: "#safety" },
] as const;

export const chapters = [
  ["Use case 1", "Daily brief", "Review calendar, inbox, notes, and open loops before the day starts."],
  ["Use case 2", "Research desk", "Let an agent collect context, summarize sources, and create workspace files."],
  ["Use case 3", "Follow-up engine", "Prepare replies and task updates without sending until you approve."],
  ["Use case 4", "Second brain", "Turn recurring facts and preferences into memory your agents can use."],
] as const;

export const modelCards = [
  {
    name: "Fast",
    description: "Quick triage, summaries, and small edits.",
    badge: "low latency",
    color: "bg-lime-100 text-lime-900",
  },
  {
    name: "Advanced",
    description: "Planning, reasoning, and complex agent runs.",
    badge: "deep work",
    color: "bg-sky-100 text-sky-900",
  },
  {
    name: "Hosted",
    description: "Default Koraku hosted model lane.",
    badge: "balanced",
    color: "bg-orange-100 text-orange-900",
  },
  {
    name: "Custom",
    description: "Bring your own provider and routing rules.",
    badge: "BYO key",
    color: "bg-violet-100 text-violet-900",
  },
] as const;

export const integrationCards = [
  { name: "Gmail", toolkit: "GMAIL", detail: "Inbox context and drafts" },
  { name: "Google Drive", toolkit: "GOOGLEDRIVE", detail: "Docs, folders, and files" },
  { name: "Slack", toolkit: "SLACK", detail: "Team context and updates" },
  { name: "Notion", toolkit: "NOTION", detail: "Pages and knowledge base" },
  { name: "Airtable", toolkit: "AIRTABLE", detail: "Tables and records" },
  { name: "Asana", toolkit: "ASANA", detail: "Tasks and project status" },
  { name: "Box", toolkit: "BOX", detail: "Enterprise file access" },
  { name: "iMessage", toolkit: "imessage", detail: "Phone and voice-note threads" },
] as const;
