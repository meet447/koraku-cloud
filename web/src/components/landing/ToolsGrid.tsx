import { integrationShowcase } from "@/components/landing/landing-data";
import { LANDING_CONTAINER, LANDING_PAGE_BG, LANDING_SECTION, LANDING_SURFACE } from "@/components/landing/landing-layout";
import { toolkitIconUrl } from "@/lib/toolkit-icons";

function integrationIcon(iconSlug: string, hex?: string) {
  return toolkitIconUrl(iconSlug, hex);
}

export function ToolsGrid() {
  return (
    <section id="integrations" className={`${LANDING_PAGE_BG} ${LANDING_SECTION}`}>
      <div className={LANDING_CONTAINER}>
        <h2 className="landing-pixel-headline max-w-3xl text-[3.2rem] font-semibold leading-[0.95] tracking-[-0.06em] text-[#282522] sm:text-[4.8rem]">
          Connect the tools agents need
        </h2>
        <p className="mt-4 max-w-2xl text-base leading-7 text-stone-500 sm:text-[17px]">
          Koraku supports <span className="font-semibold text-stone-700">35+ connections</span>{" "}
          across email, docs, chat, CRM, dev tools, and more — so agents can read context
          and act inside the apps you already use.
        </p>
        <div className="mt-10 grid grid-cols-4 gap-3 rounded-xl border border-black/10 bg-white p-4 shadow-[10px_10px_0_rgba(0,0,0,0.04)] sm:grid-cols-8">
          {integrationShowcase.map((integration) => (
            <div
              key={integration.toolkit}
              className={`flex min-h-[108px] flex-col items-center justify-center rounded-lg border border-black/10 ${LANDING_SURFACE} px-2 py-5 text-center transition hover:border-black/20 hover:bg-white`}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={integrationIcon(integration.iconSlug, "hex" in integration ? integration.hex : undefined)}
                alt=""
                width={32}
                height={32}
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
      </div>
    </section>
  );
}
