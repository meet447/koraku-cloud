"use client";

import { Cpu } from "lucide-react";
import { useEffect, useState } from "react";
import { LANDING_CONTAINER, LANDING_FOOTER_BG, LANDING_PAGE_BG, LANDING_SECTION, LANDING_SURFACE } from "@/components/landing/landing-layout";
import { modelUseCases } from "@/components/landing/landing-data";
import {
  fetchLandingLlmModels,
  type LandingLlmModel,
  resolveModelLogo,
} from "@/lib/llm-catalog";

function ModelIcon({ model }: { model: LandingLlmModel }) {
  const logoUrl = resolveModelLogo(model);
  if (logoUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={logoUrl}
        alt=""
        width={52}
        height={52}
        className="h-[52px] w-[52px] object-contain"
        loading="lazy"
        referrerPolicy="no-referrer-when-downgrade"
      />
    );
  }
  return (
    <span className="flex h-[52px] w-[52px] items-center justify-center rounded-md bg-stone-100 text-stone-500">
      <Cpu className="h-5 w-5" aria-hidden />
    </span>
  );
}

export function ModelsSection() {
  const [models, setModels] = useState<LandingLlmModel[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const next = await fetchLandingLlmModels();
      if (!cancelled) {
        setModels(next);
        setLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section id="models" className={`scroll-mt-24 ${LANDING_PAGE_BG} ${LANDING_SECTION}`}>
      <div className={LANDING_CONTAINER}>
        <h2 className="landing-pixel-headline max-w-3xl text-[3.2rem] font-semibold leading-[0.95] tracking-[-0.06em] text-[#282522] sm:text-[4.8rem]">
          Multiple LLMs, one composer
        </h2>
        <p className="mt-4 max-w-2xl text-base leading-7 text-stone-500 sm:text-[17px]">
          Switch models per message in the composer — fast summaries, deep reasoning, and defaults
          included with your Koraku plan.
        </p>

        <div className="mt-10 grid grid-cols-2 gap-4 rounded-xl border border-black/10 bg-white p-4 shadow-[10px_10px_0_rgba(0,0,0,0.04)] lg:grid-cols-4">
          {!loaded
            ? Array.from({ length: 4 }, (_, index) => (
                <div
                  key={`skeleton-${index}`}
                  className={`flex min-h-[160px] flex-col items-center justify-center rounded-lg border border-black/10 ${LANDING_SURFACE} px-5 py-8`}
                >
                  <div className="h-[52px] w-[52px] animate-pulse rounded-md bg-stone-200" />
                  <div className="mt-5 h-4 w-24 animate-pulse rounded bg-stone-200" />
                </div>
              ))
            : models.map((model) => (
                <article
                  key={model.id}
                  className={`flex min-h-[160px] flex-col items-center justify-center rounded-lg border border-black/10 ${LANDING_SURFACE} px-5 py-8 transition hover:border-black/20 hover:bg-white`}
                >
                  <ModelIcon model={model} />
                  <h3 className="mt-5 text-base font-semibold text-stone-900">{model.label}</h3>
                </article>
              ))}
        </div>

        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {modelUseCases.map((item) => (
            <div
              key={item.label}
              className={`rounded-lg border border-black/10 ${LANDING_SURFACE} px-5 py-5 shadow-[6px_6px_0_rgba(0,0,0,0.03)]`}
            >
              <p className="text-sm font-semibold text-stone-900">{item.label}</p>
              <p className="mt-2 text-sm leading-relaxed text-stone-500">{item.detail}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
