import { integrationCards } from "@/components/landing/landing-data";
import { automationToolkitIconUrl, toolkitIconUrl } from "@/lib/toolkit-icons";

function integrationIcon(toolkit: string) {
  if (toolkit === "imessage") {
    return toolkitIconUrl("imessage", "34C759");
  }
  return automationToolkitIconUrl(toolkit);
}

export function ToolsGrid() {
  return (
    <section id="integrations" className="bg-[#f8f8f7] px-5 py-28 sm:px-8">
      <div className="mx-auto max-w-[980px] text-center">
        <h2 className="landing-pixel-headline font-landing-serif text-4xl font-semibold leading-[0.95] tracking-[-0.06em] text-[#282522] sm:text-5xl">
          Connect the tools agents need
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-sm leading-6 text-stone-500">
          Koraku agents can read context from your apps, prepare drafts, and keep every
          high-impact external action behind approval.
        </p>
        <div className="mx-auto mt-12 grid max-w-4xl grid-cols-2 gap-3 rounded-lg border border-black/10 bg-white p-3 shadow-[10px_10px_0_rgba(0,0,0,0.04)] sm:grid-cols-4">
          {integrationCards.map((integration) => (
            <div
              key={integration.name}
              className="rounded-md border border-black/10 bg-[#f8f8f7] p-4 text-left"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={integrationIcon(integration.toolkit)}
                alt=""
                width={28}
                height={28}
                className="h-7 w-7 object-contain"
              />
              <p className="mt-4 text-sm font-semibold text-stone-800">{integration.name}</p>
              <p className="mt-1 text-xs leading-5 text-stone-500">{integration.detail}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
