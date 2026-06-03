import { LegalDocument } from "@/components/landing/LegalDocument";
import { LegalPageLayout } from "@/components/landing/LegalPageLayout";
import { cookiesDocument } from "@/lib/legal-content";
import { legalMetadata } from "@/lib/legal-metadata";
import { legalPages } from "@/lib/legal-pages";

const meta = legalPages.find((p) => p.slug === "cookies")!;

export const metadata = legalMetadata(meta.label, meta.description);

export default function CookiesPage() {
  return (
    <LegalPageLayout activeSlug="cookies">
      <LegalDocument content={cookiesDocument} />
    </LegalPageLayout>
  );
}
