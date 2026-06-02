import {
  Brain,
  FolderOpen,
  MessageCircle,
  Plug,
  ShieldCheck,
  Workflow,
  type LucideIcon,
} from "lucide-react";

type Feature = {
  icon: LucideIcon;
  title: string;
  description: string;
};

const FEATURES: Feature[] = [
  {
    icon: Brain,
    title: "Memory",
    description:
      "A living second brain that learns your preferences and recalls context from past conversations—automatically.",
  },
  {
    icon: FolderOpen,
    title: "Workspace",
    description:
      "A cloud workspace where Koraku drafts documents, organizes files, and keeps your work in one searchable place.",
  },
  {
    icon: Plug,
    title: "Connections",
    description:
      "Link Gmail, Slack, Notion, Drive and more so Koraku can read context and take action across your tools.",
  },
  {
    icon: Workflow,
    title: "Automations",
    description:
      "Turn recurring work into scheduled automations that run in the background and ask before high-impact actions.",
  },
  {
    icon: MessageCircle,
    title: "iMessage & SMS",
    description:
      "Text or send voice notes to Koraku from your phone. Linked threads sync straight to the web, like any chat.",
  },
  {
    icon: ShieldCheck,
    title: "Safe by design",
    description:
      "Koraku confirms before sending messages, sharing files, or anything high-impact. Your data stays in your account.",
  },
];

export function CoreFeatures() {
  return (
    <section
      id="features"
      className="scroll-mt-20 bg-white px-5 py-20 font-landing-sans md:px-6 md:py-28"
      aria-labelledby="core-features-title"
    >
      <div className="mx-auto w-full max-w-[1120px]">
        <header className="mx-auto max-w-2xl text-center">
          <p className="mb-4 text-xs font-semibold uppercase tracking-[0.2em] text-landing-accentText">
            Everything Koraku does
          </p>
          <h2
            id="core-features-title"
            className="text-[2.1rem] font-medium leading-tight tracking-tight text-landing-ink sm:text-[2.6rem]"
          >
            One place for memory, work, and momentum
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-landing-muted md:text-lg">
            A hosted AI companion that ties your context, apps, and routines together—so
            you can pick up exactly where you left off.
          </p>
        </header>

        <div className="mt-14 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <article
              key={title}
              className="flex flex-col rounded-2xl border border-black/[0.06] bg-landing-shell p-7 transition-shadow hover:shadow-landing-soft"
            >
              <span className="flex h-12 w-12 items-center justify-center rounded-xl border border-orange-200 bg-landing-accentSoft text-landing-accent">
                <Icon className="h-6 w-6" strokeWidth={1.75} aria-hidden />
              </span>
              <h3 className="mt-5 text-lg font-semibold text-landing-ink">{title}</h3>
              <p className="mt-2 text-[15px] leading-relaxed text-landing-muted">{description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
