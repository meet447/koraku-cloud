import { LEGAL_CONTACT, LEGAL_LAST_UPDATED } from "@/lib/legal-pages";
import { KORAKU_COPY } from "@/lib/korakuBrand";

export type LegalBlock =
  | { type: "p"; text: string }
  | { type: "ul"; items: string[] };

export type LegalSection = {
  id: string;
  title: string;
  blocks: LegalBlock[];
};

export type LegalDocumentContent = {
  title: string;
  subtitle: string;
  badge?: string;
  sections: LegalSection[];
};

const sharedIntro =
  "Koraku is a hosted software service. You sign in with your account, connect third-party apps through OAuth where available, and use agents, workspace files, memory, and automations in the cloud.";

export const privacyDocument: LegalDocumentContent = {
  title: "Privacy Policy",
  subtitle: "How Koraku handles information in your account and connected apps.",
  badge: "Legal",
  sections: [
    {
      id: "overview",
      title: "Overview",
      blocks: [
        { type: "p", text: sharedIntro },
        {
          type: "p",
          text: "This policy describes what we collect, why we use it, and the choices you have. It applies to the Koraku website, web application, and related services operated by Koraku.",
        },
      ],
    },
    {
      id: "collect",
      title: "Information we collect",
      blocks: [
        {
          type: "ul",
          items: [
            "Account information from your sign-in provider (such as name, email, and profile identifier) when you authenticate with Google or GitHub.",
            "Product data you create in Koraku: chat messages, agent instructions, personalization, learned memory, automation definitions, automation run history, and files in your cloud workspace.",
            "Connected app data that you authorize through OAuth or similar flows — for example email metadata, documents, tasks, or calendar events needed to fulfill your instructions.",
            "Device and usage information such as browser type, approximate region, and interaction logs used to operate, secure, and improve the service.",
            "Messaging identifiers if you link iMessage or SMS, including verified phone numbers and message content needed to run conversations.",
          ],
        },
      ],
    },
    {
      id: "use",
      title: "How we use information",
      blocks: [
        { type: "p", text: KORAKU_COPY.privacyProcessing },
        { type: "p", text: KORAKU_COPY.privacyStorage },
        {
          type: "ul",
          items: [
            "Provide chat, workspace, memory, automations, and connected-app actions you request.",
            "Authenticate you, prevent abuse, and maintain the security of the service.",
            "Improve reliability, debug issues, and develop new product features.",
            "Communicate with you about service changes, security notices, or support requests.",
          ],
        },
      ],
    },
    {
      id: "sharing",
      title: "When we share information",
      blocks: [
        {
          type: "p",
          text: "We do not sell your personal information. We share data only as needed to run the service, including with infrastructure and integration providers that process data on our behalf under contractual obligations. Connected apps receive only the actions you approve or that your instructions require.",
        },
        {
          type: "ul",
          items: [
            "Service providers that host databases, authentication, model inference, messaging, or integration tooling.",
            "Third-party applications you connect, when you direct Koraku to read or update data in those apps.",
            "Authorities when required by law or to protect rights, safety, and security.",
          ],
        },
      ],
    },
    {
      id: "retention",
      title: "Retention",
      blocks: [
        {
          type: "p",
          text: "We retain account and product data while your account is active and as needed to provide the service. You can export or delete Koraku-owned app data from Settings. Some long-term learned memory may be retained separately and is not cleared by a standard data deletion request, as described in product settings.",
        },
        {
          type: "p",
          text: "After deletion, we may retain limited backups or logs for a short period for security, fraud prevention, and legal compliance before they are purged.",
        },
      ],
    },
    {
      id: "choices",
      title: "Your choices",
      blocks: [
        {
          type: "ul",
          items: [
            "Review and update personalization and memory in the app.",
            "Disconnect third-party apps from Settings at any time.",
            "Export or delete Koraku app data from Settings.",
            "Sign out and revoke sessions through your account provider where applicable.",
            "Contact us for privacy questions or requests at the address on our Contact page.",
          ],
        },
        {
          type: "p",
          text: "Do not store passwords, payment card numbers, or other secrets in chat or memory. Koraku is designed to ask for confirmation before high-impact external actions such as sending messages, changing calendars, sharing files, or modifying records in connected apps.",
        },
      ],
    },
    {
      id: "children",
      title: "Children",
      blocks: [
        {
          type: "p",
          text: "Koraku is not directed to children under 13 (or the minimum age required in your country). We do not knowingly collect personal information from children. Contact us if you believe a child has provided data through the service.",
        },
      ],
    },
    {
      id: "changes",
      title: "Changes to this policy",
      blocks: [
        {
          type: "p",
          text: `We may update this policy from time to time. We will post the revised version on this page and update the “Last updated” date. Material changes may be communicated through the app or by email where appropriate.`,
        },
      ],
    },
    {
      id: "contact",
      title: "Contact",
      blocks: [
        {
          type: "p",
          text: `Privacy questions and requests: ${LEGAL_CONTACT.privacy}. General support: ${LEGAL_CONTACT.support}. See also our Contact page.`,
        },
      ],
    },
  ],
};

export const termsDocument: LegalDocumentContent = {
  title: "Terms of Service",
  subtitle: "The agreement between you and Koraku for use of the hosted service.",
  badge: "Legal",
  sections: [
    {
      id: "agreement",
      title: "Agreement",
      blocks: [
        {
          type: "p",
          text: "By accessing or using Koraku, you agree to these Terms of Service and our Privacy Policy. If you do not agree, do not use the service.",
        },
        { type: "p", text: sharedIntro },
      ],
    },
    {
      id: "service",
      title: "The service",
      blocks: [
        {
          type: "p",
          text: "Koraku provides AI-assisted chat, memory, workspace files, app connections, and automations through a hosted web application. Features may change during early access; we may add, modify, or remove functionality with reasonable notice where practical.",
        },
        {
          type: "p",
          text: "Model outputs and automations can be incorrect or incomplete. You are responsible for reviewing results before relying on them or allowing external actions.",
        },
      ],
    },
    {
      id: "account",
      title: "Your account",
      blocks: [
        {
          type: "ul",
          items: [
            "You must provide accurate information and keep your sign-in credentials secure.",
            "You are responsible for activity under your account, including actions taken by automations you configure.",
            "You must be old enough to form a binding contract in your jurisdiction and meet any minimum age in our Privacy Policy.",
            "We may suspend or terminate accounts that violate these terms or pose a security risk.",
          ],
        },
      ],
    },
    {
      id: "acceptable-use",
      title: "Acceptable use",
      blocks: [
        {
          type: "p",
          text: "You may not misuse Koraku. Prohibited conduct includes:",
        },
        {
          type: "ul",
          items: [
            "Violating law or third-party rights, including intellectual property and privacy rights.",
            "Sending spam, malware, or abusive content through connected channels.",
            "Attempting to bypass security, rate limits, or approval gates.",
            "Using the service for regulated, emergency, medical, financial, or other high-stakes decisions without human review.",
            "Scraping, reverse engineering, or reselling the service except as expressly permitted.",
            "Uploading unlawful content or using Koraku to harass others.",
          ],
        },
      ],
    },
    {
      id: "connections",
      title: "Connected apps",
      blocks: [
        {
          type: "p",
          text: "When you connect third-party applications, you authorize Koraku to access data and perform actions according to your instructions and in-app approvals. Those services have their own terms and privacy policies. Disconnect apps from Settings when you no longer want Koraku to access them.",
        },
      ],
    },
    {
      id: "content",
      title: "Your content",
      blocks: [
        {
          type: "p",
          text: "You retain ownership of content you submit. You grant Koraku a limited license to host, process, and display that content solely to operate and improve the service. You represent that you have the rights needed for us to do so.",
        },
      ],
    },
    {
      id: "beta",
      title: "Early access",
      blocks: [
        {
          type: "p",
          text: "Koraku may be offered as an early-access or beta service. You may experience outages, incomplete integrations, or errors. We provide the service on an “as is” and “as available” basis to the fullest extent permitted by law.",
        },
      ],
    },
    {
      id: "liability",
      title: "Disclaimer and limitation of liability",
      blocks: [
        {
          type: "p",
          text: "To the maximum extent permitted by law, Koraku and its operators disclaim warranties of merchantability, fitness for a particular purpose, and non-infringement. We are not liable for indirect, incidental, special, consequential, or punitive damages, or for loss of profits, data, or goodwill arising from your use of the service.",
        },
        {
          type: "p",
          text: "Our total liability for any claim relating to the service is limited to the greater of amounts you paid us for the service in the twelve months before the claim or one hundred U.S. dollars, except where such limitation is not allowed by law.",
        },
      ],
    },
    {
      id: "termination",
      title: "Termination",
      blocks: [
        {
          type: "p",
          text: "You may stop using Koraku at any time. You may delete Koraku app data from Settings. We may suspend or end access for violations of these terms or to protect the service. Sections that by nature should survive termination will survive.",
        },
      ],
    },
    {
      id: "law",
      title: "Governing law",
      blocks: [
        {
          type: "p",
          text: "These terms are governed by the laws applicable to Koraku’s operator, without regard to conflict-of-law rules. Disputes will be resolved in the courts or forums specified by applicable law unless otherwise required by consumer protection rules in your country.",
        },
      ],
    },
    {
      id: "contact",
      title: "Contact",
      blocks: [
        {
          type: "p",
          text: `Questions about these terms: ${LEGAL_CONTACT.support}.`,
        },
      ],
    },
  ],
};

export const securityDocument: LegalDocumentContent = {
  title: "Security",
  subtitle: "How we approach account safety, approvals, and responsible disclosure.",
  badge: "Trust",
  sections: [
    {
      id: "commitment",
      title: "Our commitment",
      blocks: [
        {
          type: "p",
          text: "Koraku is built for real work: connected accounts, agent actions, and cloud workspace files. Security is part of product design — not an afterthought.",
        },
      ],
    },
    {
      id: "account",
      title: "Account security",
      blocks: [
        {
          type: "ul",
          items: [
            "Sign-in through established OAuth providers (Google, GitHub) — we do not store your provider password.",
            "Session handling via secure, HTTP-only cookies where applicable.",
            "Organization and tenant boundaries for team workspaces when enabled.",
          ],
        },
      ],
    },
    {
      id: "actions",
      title: "Ask before acting",
      blocks: [
        {
          type: "p",
          text: "Koraku is designed to confirm before high-impact external actions such as sending messages, sharing files, or changing records in connected apps. Review proposed actions in the app before they run.",
        },
        {
          type: "p",
          text: "Automations inherit the same approval expectations. Scope automations narrowly and avoid high-stakes workflows without human review.",
        },
      ],
    },
    {
      id: "data",
      title: "Data handling",
      blocks: [
        { type: "p", text: KORAKU_COPY.privacyStorage },
        {
          type: "p",
          text: "Workspace paths, tool policies, and server-side checks help constrain what agents can access. Do not store secrets in chat or memory.",
        },
      ],
    },
    {
      id: "connections",
      title: "Connected apps",
      blocks: [
        {
          type: "p",
          text: "Third-party connections use industry-standard OAuth where supported. You can revoke access from Koraku Settings or from the provider’s security settings. Koraku only uses the scopes needed to fulfill your instructions.",
        },
      ],
    },
    {
      id: "reporting",
      title: "Reporting vulnerabilities",
      blocks: [
        {
          type: "p",
          text: `If you discover a security issue, please report it privately to ${LEGAL_CONTACT.security}. Do not file public issues for vulnerabilities. Include a description, impact, and steps to reproduce. We aim to acknowledge reports within 72 hours.`,
        },
      ],
    },
  ],
};

export const cookiesDocument: LegalDocumentContent = {
  title: "Cookie Policy",
  subtitle: "Cookies and similar technologies on koraku.app.",
  badge: "Legal",
  sections: [
    {
      id: "what",
      title: "What are cookies",
      blocks: [
        {
          type: "p",
          text: "Cookies are small text files stored on your device. We use cookies and similar storage (such as local session storage) to operate the Koraku web application.",
        },
      ],
    },
    {
      id: "essential",
      title: "Essential cookies",
      blocks: [
        {
          type: "p",
          text: "These are required for the service to function. They cannot be switched off in our systems.",
        },
        {
          type: "ul",
          items: [
            "Authentication and session cookies to keep you signed in securely.",
            "Security and load-balancing cookies that help protect the service.",
            "Preference cookies that remember settings within your session or account.",
          ],
        },
      ],
    },
    {
      id: "analytics",
      title: "Analytics",
      blocks: [
        {
          type: "p",
          text: "We may use privacy-conscious analytics to understand usage and improve the product. If we enable optional analytics cookies, we will describe them here and provide choices where required by law.",
        },
      ],
    },
    {
      id: "third-party",
      title: "Third-party sign-in",
      blocks: [
        {
          type: "p",
          text: "When you sign in with Google or GitHub, those providers may set their own cookies on their domains. Their use is governed by their respective policies.",
        },
      ],
    },
    {
      id: "control",
      title: "Your choices",
      blocks: [
        {
          type: "ul",
          items: [
            "Sign out to end your Koraku session.",
            "Clear cookies through your browser settings (you may need to sign in again).",
            "Block cookies in your browser — note that essential features may not work.",
          ],
        },
      ],
    },
    {
      id: "contact",
      title: "Contact",
      blocks: [
        {
          type: "p",
          text: `Questions about cookies: ${LEGAL_CONTACT.privacy}.`,
        },
      ],
    },
  ],
};

export const contactDocument: LegalDocumentContent = {
  title: "Contact",
  subtitle: "How to reach Koraku for support, privacy, and security.",
  badge: "Help",
  sections: [
    {
      id: "support",
      title: "Product support",
      blocks: [
        {
          type: "p",
          text: `For help using Koraku — connections, automations, workspace, or billing questions — email ${LEGAL_CONTACT.support}. Include your account email and a short description of the issue.`,
        },
        {
          type: "p",
          text: "Many tasks can also be managed directly in the app under Settings, including exporting data, deleting Koraku app data, and disconnecting apps.",
        },
      ],
    },
    {
      id: "privacy",
      title: "Privacy requests",
      blocks: [
        {
          type: "p",
          text: `For privacy questions, data access requests, or corrections, contact ${LEGAL_CONTACT.privacy}. We will respond within a reasonable timeframe as required by applicable law.`,
        },
        { type: "p", text: "See our Privacy Policy for details on what we collect and how to delete data from Settings." },
      ],
    },
    {
      id: "security",
      title: "Security reports",
      blocks: [
        {
          type: "p",
          text: `Report vulnerabilities privately to ${LEGAL_CONTACT.security}. Please do not disclose security issues publicly before we have had a chance to address them.`,
        },
        { type: "p", text: "See our Security page for more on how we handle reports." },
      ],
    },
    {
      id: "legal",
      title: "Legal notices",
      blocks: [
        {
          type: "p",
          text: "Formal legal notices may be sent to the privacy contact above with “Legal notice” in the subject line.",
        },
      ],
    },
  ],
};
