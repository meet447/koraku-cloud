export const navItems = [
  { label: "Use cases", href: "#how-to" },
  { label: "Models", href: "#models" },
  { label: "Integrations", href: "#integrations" },
] as const;

export const chapters = [
  ["Use case 1", "Daily brief", "Review calendar, inbox, notes, and open loops before the day starts."],
  ["Use case 2", "Research desk", "Let an agent collect context, summarize sources, and create workspace files."],
  ["Use case 3", "Follow-up engine", "Prepare replies and task updates without sending until you approve."],
  ["Use case 4", "Second brain", "Turn recurring facts and preferences into memory your agents can use."],
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
