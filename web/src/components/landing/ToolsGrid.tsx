import Image from "next/image";
import {
  integrationCategories,
  integrationShowcase,
  popularWorkflows,
} from "@/components/landing/landing-data";
import { LANDING_CONTAINER, LANDING_PAGE_BG, LANDING_SECTION, LANDING_SURFACE } from "@/components/landing/landing-layout";
import { toolkitIconUrl } from "@/lib/toolkit-icons";

function integrationIcon(iconSlug: string, hex?: string) {
  return toolkitIconUrl(iconSlug, hex);
}

export function ToolsGrid() {
  return (
    <section id="integrations" className={`scroll-mt-24 ${LANDING_PAGE_BG} ${LANDING_SECTION}`}>
      <div className={LANDING_CONTAINER}>
        <h2 className="landing-pixel-headline max-w-3xl text-[3.2rem] font-semibold leading-[0.95] tracking-[-0.06em] text-[#282522] sm:text-[4.8rem]">
          Connect the tools agents need
        </h2>
        <p className="mt-4 max-w-2xl text-base leading-7 text-stone-500 sm:text-[17px]">
          Koraku supports <span className="font-semibold text-stone-700">35+ connections</span>{" "}
          across email, docs, chat, CRM, dev tools, and more. Connect once in Settings → Connected
          apps; revoke anytime.
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          {integrationCategories.map((category) => (
            <span
              key={category}
              className="rounded-full border border-black/10 bg-white px-3 py-1 text-xs font-semibold text-stone-600 shadow-sm"
            >
              {category}
            </span>
          ))}
        </div>
        <div className="mt-8 grid grid-cols-4 gap-3 rounded-xl border border-black/10 bg-white p-4 shadow-[10px_10px_0_rgba(0,0,0,0.04)] sm:grid-cols-8">
          {integrationShowcase.map((integration) => (
            <div
              key={integration.toolkit}
              className={`flex min-h-[108px] flex-col items-center justify-center rounded-lg border border-black/10 ${LANDING_SURFACE} px-2 py-5 text-center transition hover:border-black/20 hover:bg-white`}
            >
              <Image
                src={integrationIcon(integration.iconSlug, "hex" in integration ? integration.hex : undefined)}
                alt=""
                width={32}
                height={32}
                unoptimized
                className="h-8 w-8 object-contain"
              />
              <p className="mt-3 text-xs font-semibold leading-4 text-stone-700">
                {integration.name}
              </p>
            </div>
          ))}
        </div>
        <p className="mt-5 text-sm text-stone-400">
          Plus Stripe, Shopify, Salesforce, Slack, Confluence, and more.
        </p>

        <div className="mt-10 rounded-lg border border-black/10 bg-white p-6 shadow-[10px_10px_0_rgba(0,0,0,0.03)]">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-400">
            Popular workflows
          </p>
          <ul className="mt-4 grid gap-3 sm:grid-cols-2">
            {popularWorkflows.map((workflow) => (
              <li
                key={workflow}
                className="flex gap-2 text-sm leading-relaxed text-stone-600"
              >
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-orange-500" aria-hidden />
                {workflow}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
