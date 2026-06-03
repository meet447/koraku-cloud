import { LegalDocument } from "@/components/landing/LegalDocument";
import { LegalPageLayout } from "@/components/landing/LegalPageLayout";
import { securityDocument } from "@/lib/legal-content";
import { legalMetadata } from "@/lib/legal-metadata";
import { legalPages } from "@/lib/legal-pages";

const meta = legalPages.find((p) => p.slug === "security")!;

export const metadata = legalMetadata(meta.label, meta.description);

export default function SecurityPage() {
  return (
    <LegalPageLayout activeSlug="security">
      <LegalDocument content={securityDocument} />
    </LegalPageLayout>
  );
}
