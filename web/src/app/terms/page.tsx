import Link from "next/link";

export default function TermsPage() {
  return (
    <main className="mx-auto min-h-dvh max-w-3xl px-6 py-16">
      <p className="text-xs font-bold uppercase tracking-[0.22em] text-orange-700">
        Public beta
      </p>
      <h1 className="mt-2 text-4xl font-bold tracking-tight text-neutral-950">
        Beta terms
      </h1>
      <div className="mt-8 space-y-5 text-sm font-medium leading-relaxed text-neutral-700">
        <p>
          Koraku is an early-access assistant for memory, research, workspace artifacts,
          and automations. Expect occasional errors, provider outages, and incomplete
          integrations while the product is in beta.
        </p>
        <p>
          Review important outputs before relying on them. You are responsible for
          confirming external actions, recipients, dates, files, and connected accounts
          before Koraku sends, shares, schedules, deletes, or modifies data.
        </p>
        <p>
          Automations should be scoped, reversible, and safe. Avoid using beta automations
          for regulated, emergency, financial, medical, or other high-stakes workflows.
        </p>
      </div>
      <Link href="/" className="mt-8 inline-flex text-sm font-bold text-orange-700 underline">
        Back home
      </Link>
    </main>
  );
}
