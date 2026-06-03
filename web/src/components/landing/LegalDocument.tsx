import Link from "next/link";
import type { LegalDocumentContent } from "@/lib/legal-content";
import { LEGAL_LAST_UPDATED, legalPages } from "@/lib/legal-pages";

export function LegalDocument({ content }: { content: LegalDocumentContent }) {
  return (
    <article>
      {content.badge ? (
        <p className="inline-block rounded bg-white px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-stone-500 shadow-sm ring-1 ring-black/5">
          {content.badge}
        </p>
      ) : null}
      <h1 className="landing-pixel-headline mt-4 text-[2.6rem] font-semibold leading-[0.92] tracking-[-0.06em] text-[#282522] sm:text-[3.4rem]">
        {content.title}
      </h1>
      <p className="mt-3 max-w-2xl text-base font-medium leading-7 text-stone-500">{content.subtitle}</p>
      <p className="mt-2 text-xs font-medium text-stone-400">Last updated {LEGAL_LAST_UPDATED}</p>

      <nav
        className="mt-8 rounded-lg border border-black/10 bg-white p-5 shadow-[6px_6px_0_rgba(0,0,0,0.03)]"
        aria-label="On this page"
      >
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-stone-400">On this page</p>
        <ul className="mt-3 flex flex-col gap-2 sm:columns-2 sm:gap-x-8">
          {content.sections.map((section) => (
            <li key={section.id} className="break-inside-avoid">
              <a
                href={`#${section.id}`}
                className="text-sm font-medium text-stone-600 transition hover:text-stone-900"
              >
                {section.title}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <div className="mt-10 space-y-10">
        {content.sections.map((section) => (
          <section key={section.id} id={section.id} className="scroll-mt-28">
            <h2 className="text-xl font-semibold tracking-tight text-stone-900">{section.title}</h2>
            <div className="mt-4 space-y-4">
              {section.blocks.map((block, index) => {
                if (block.type === "p") {
                  return (
                    <p key={index} className="text-[15px] leading-relaxed text-stone-600">
                      {block.text}
                    </p>
                  );
                }
                return (
                  <ul key={index} className="list-disc space-y-2 pl-5 text-[15px] leading-relaxed text-stone-600">
                    {block.items.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                );
              })}
            </div>
          </section>
        ))}
      </div>

      <aside className="mt-12 rounded-lg border border-black/10 bg-[#fafafa] p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-stone-400">Related policies</p>
        <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-2">
          {legalPages.map((page) => (
            <li key={page.slug}>
              <Link href={page.href} className="text-sm font-semibold text-stone-700 hover:text-stone-950">
                {page.label}
              </Link>
            </li>
          ))}
        </ul>
      </aside>
    </article>
  );
}
