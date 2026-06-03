import { LegalDocument } from "@/components/landing/LegalDocument";
import { LegalPageLayout } from "@/components/landing/LegalPageLayout";
import { termsDocument } from "@/lib/legal-content";
import { legalMetadata } from "@/lib/legal-metadata";
import { legalPages } from "@/lib/legal-pages";

const meta = legalPages.find((p) => p.slug === "terms")!;

export const metadata = legalMetadata(meta.label, meta.description);

export default function TermsPage() {
  return (
    <LegalPageLayout activeSlug="terms">
      <LegalDocument content={termsDocument} />
    </LegalPageLayout>
  );
}
