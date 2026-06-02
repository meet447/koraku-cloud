import { OAuthSignInButtons } from "@/components/OAuthSignInButtons";
import { KorakuAuthShell } from "@/components/KorakuAuthShell";
import { AuthPageLayout } from "@/components/landing/AuthPageLayout";

export const dynamic = "force-dynamic";

export default function SignInPage() {
  return (
    <AuthPageLayout>
      <KorakuAuthShell
        title="Continue with Koraku"
        description="Sign in with Google or GitHub. New accounts are created automatically on first sign-in."
      >
        <OAuthSignInButtons />
      </KorakuAuthShell>
    </AuthPageLayout>
  );
}
