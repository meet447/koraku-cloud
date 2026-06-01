"""Curated Connections catalog — ~40 widely used integrations (Composio slugs)."""

from __future__ import annotations

from typing import Literal, TypedDict

CategoryId = Literal["dev", "collab", "docs"]


class CuratedToolkit(TypedDict):
    slug: str
    name: str
    description: str
    category: CategoryId
    icon_slug: str


# Order = display priority. Unsupported slugs are omitted when resolved against Composio.
CURATED_TOOLKITS: tuple[CuratedToolkit, ...] = (
    {
        "slug": "GMAIL",
        "name": "Gmail",
        "description": "Read, search, and send email from Koraku.",
        "category": "collab",
        "icon_slug": "gmail",
    },
    {
        "slug": "GOOGLECALENDAR",
        "name": "Google Calendar",
        "description": "View events and schedule meetings.",
        "category": "collab",
        "icon_slug": "googlecalendar",
    },
    {
        "slug": "GOOGLEDRIVE",
        "name": "Google Drive",
        "description": "Files and folders in your Drive.",
        "category": "docs",
        "icon_slug": "googledrive",
    },
    {
        "slug": "GOOGLESHEETS",
        "name": "Google Sheets",
        "description": "Spreadsheets, rows, and cell updates.",
        "category": "docs",
        "icon_slug": "googlesheets",
    },
    {
        "slug": "GOOGLEDOCS",
        "name": "Google Docs",
        "description": "Documents and collaborative editing.",
        "category": "docs",
        "icon_slug": "googledocs",
    },
    {
        "slug": "SLACK",
        "name": "Slack",
        "description": "Team chat, channels, and messages.",
        "category": "collab",
        "icon_slug": "slack",
    },
    {
        "slug": "DISCORD",
        "name": "Discord",
        "description": "Server messages and community actions.",
        "category": "collab",
        "icon_slug": "discord",
    },
    {
        "slug": "MICROSOFT_TEAMS",
        "name": "Microsoft Teams",
        "description": "Teams chat and collaboration.",
        "category": "collab",
        "icon_slug": "microsoftteams",
    },
    {
        "slug": "OUTLOOK",
        "name": "Outlook",
        "description": "Microsoft email and inbox actions.",
        "category": "collab",
        "icon_slug": "microsoftoutlook",
    },
    {
        "slug": "ZOOM",
        "name": "Zoom",
        "description": "Meetings and video calls.",
        "category": "collab",
        "icon_slug": "zoom",
    },
    {
        "slug": "GITHUB",
        "name": "GitHub",
        "description": "Repos, issues, and pull requests.",
        "category": "dev",
        "icon_slug": "github",
    },
    {
        "slug": "GITLAB",
        "name": "GitLab",
        "description": "Repositories, merge requests, and CI.",
        "category": "dev",
        "icon_slug": "gitlab",
    },
    {
        "slug": "BITBUCKET",
        "name": "Bitbucket",
        "description": "Repositories and code review.",
        "category": "dev",
        "icon_slug": "bitbucket",
    },
    {
        "slug": "JIRA",
        "name": "Jira",
        "description": "Issues, boards, and sprints.",
        "category": "dev",
        "icon_slug": "jira",
    },
    {
        "slug": "LINEAR",
        "name": "Linear",
        "description": "Issues and product workflows.",
        "category": "dev",
        "icon_slug": "linear",
    },
    {
        "slug": "NOTION",
        "name": "Notion",
        "description": "Pages and databases in your workspace.",
        "category": "docs",
        "icon_slug": "notion",
    },
    {
        "slug": "CONFLUENCE",
        "name": "Confluence",
        "description": "Wiki pages and team documentation.",
        "category": "docs",
        "icon_slug": "confluence",
    },
    {
        "slug": "AIRTABLE",
        "name": "Airtable",
        "description": "Bases, tables, and records.",
        "category": "docs",
        "icon_slug": "airtable",
    },
    {
        "slug": "ASANA",
        "name": "Asana",
        "description": "Projects, tasks, and assignments.",
        "category": "collab",
        "icon_slug": "asana",
    },
    {
        "slug": "TRELLO",
        "name": "Trello",
        "description": "Boards, lists, and cards.",
        "category": "collab",
        "icon_slug": "trello",
    },
    {
        "slug": "MONDAY",
        "name": "Monday.com",
        "description": "Workboards and project tracking.",
        "category": "collab",
        "icon_slug": "monday",
    },
    {
        "slug": "CLICKUP",
        "name": "ClickUp",
        "description": "Tasks, docs, and goals in one place.",
        "category": "collab",
        "icon_slug": "clickup",
    },
    {
        "slug": "HUBSPOT",
        "name": "HubSpot",
        "description": "CRM contacts, deals, and pipelines.",
        "category": "collab",
        "icon_slug": "hubspot",
    },
    {
        "slug": "SALESFORCE",
        "name": "Salesforce",
        "description": "CRM records and sales workflows.",
        "category": "collab",
        "icon_slug": "salesforce",
    },
    {
        "slug": "PIPEDRIVE",
        "name": "Pipedrive",
        "description": "Deals, contacts, and sales activity.",
        "category": "collab",
        "icon_slug": "pipedrive",
    },
    {
        "slug": "ZENDESK",
        "name": "Zendesk",
        "description": "Support tickets and customer requests.",
        "category": "collab",
        "icon_slug": "zendesk",
    },
    {
        "slug": "INTERCOM",
        "name": "Intercom",
        "description": "Customer conversations and support.",
        "category": "collab",
        "icon_slug": "intercom",
    },
    {
        "slug": "STRIPE",
        "name": "Stripe",
        "description": "Payments, customers, and subscriptions.",
        "category": "dev",
        "icon_slug": "stripe",
    },
    {
        "slug": "SHOPIFY",
        "name": "Shopify",
        "description": "Store orders, products, and customers.",
        "category": "collab",
        "icon_slug": "shopify",
    },
    {
        "slug": "MAILCHIMP",
        "name": "Mailchimp",
        "description": "Email campaigns and audience lists.",
        "category": "collab",
        "icon_slug": "mailchimp",
    },
    {
        "slug": "TWILIO",
        "name": "Twilio",
        "description": "SMS and messaging APIs.",
        "category": "dev",
        "icon_slug": "twilio",
    },
    {
        "slug": "SENDGRID",
        "name": "SendGrid",
        "description": "Transactional email delivery.",
        "category": "dev",
        "icon_slug": "sendgrid",
    },
    {
        "slug": "DROPBOX",
        "name": "Dropbox",
        "description": "Cloud files and shared folders.",
        "category": "docs",
        "icon_slug": "dropbox",
    },
    {
        "slug": "BOX",
        "name": "Box",
        "description": "Enterprise file storage and sharing.",
        "category": "docs",
        "icon_slug": "box",
    },
    {
        "slug": "ONEDRIVE",
        "name": "OneDrive",
        "description": "Microsoft cloud files and folders.",
        "category": "docs",
        "icon_slug": "onedrive",
    },
    {
        "slug": "FIGMA",
        "name": "Figma",
        "description": "Design files, comments, and components.",
        "category": "docs",
        "icon_slug": "figma",
    },
    {
        "slug": "CANVA",
        "name": "Canva",
        "description": "Designs and visual assets.",
        "category": "docs",
        "icon_slug": "canva",
    },
    {
        "slug": "CALENDLY",
        "name": "Calendly",
        "description": "Scheduling links and booked events.",
        "category": "collab",
        "icon_slug": "calendly",
    },
    {
        "slug": "DOCUSIGN",
        "name": "DocuSign",
        "description": "Send and track e-signatures.",
        "category": "docs",
        "icon_slug": "docusign",
    },
    {
        "slug": "SUPABASE",
        "name": "Supabase",
        "description": "Database tables and project data.",
        "category": "dev",
        "icon_slug": "supabase",
    },
)

CURATED_TOOLKIT_SLUGS: tuple[str, ...] = tuple(t["slug"] for t in CURATED_TOOLKITS)
