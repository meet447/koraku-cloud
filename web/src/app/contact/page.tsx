import Link from "next/link";
import { LegalDocument } from "@/components/landing/LegalDocument";
import { LegalPageLayout } from "@/components/landing/LegalPageLayout";
import { contactDocument } from "@/lib/legal-content";
import { legalMetadata } from "@/lib/legal-metadata";
import { LEGAL_CONTACT, legalPages } from "@/lib/legal-pages";

const meta = legalPages.find((p) => p.slug === "contact")!;

export const metadata = legalMetadata(meta.label, meta.description);

export default function ContactPage() {
  return (
    <LegalPageLayout activeSlug="contact">
      <LegalDocument content={contactDocument} />
      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        {(
          [
            { label: "Support", email: LEGAL_CONTACT.support, href: `mailto:${LEGAL_CONTACT.support}` },
            { label: "Privacy", email: LEGAL_CONTACT.privacy, href: `mailto:${LEGAL_CONTACT.privacy}` },
            { label: "Security", email: LEGAL_CONTACT.security, href: `mailto:${LEGAL_CONTACT.security}` },
          ] as const
        ).map((item) => (
          <a
            key={item.label}
            href={item.href}
            className="rounded-lg border border-black/10 bg-white p-5 shadow-[6px_6px_0_rgba(0,0,0,0.03)] transition hover:border-black/20"
          >
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-stone-400">{item.label}</p>
            <p className="mt-2 text-sm font-semibold text-stone-800">{item.email}</p>
          </a>
        ))}
      </div>
      <p className="mt-6 text-sm text-stone-500">
        Prefer the app? Open{" "}
        <Link href="/app/settings" className="font-semibold text-stone-700 underline-offset-2 hover:underline">
          Settings
        </Link>{" "}
        to manage data and connections.
      </p>
    </LegalPageLayout>
  );
}
