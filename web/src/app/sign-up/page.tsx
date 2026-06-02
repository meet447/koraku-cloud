import Link from "next/link";
import { OAuthSignInButtons } from "@/components/OAuthSignInButtons";
import { KorakuAuthShell } from "@/components/KorakuAuthShell";

export const dynamic = "force-dynamic";

export default function SignUpPage() {
  return (
    <KorakuAuthShell
      title="Create account"
      description={
        <>
          Sign in with Google or GitHub to create your Koraku account, then teach Koraku
          how to help you. Already have one?{" "}
          <Link href="/sign-in" className="font-semibold text-koraku-ink underline">
            Sign in
          </Link>
        </>
      }
    >
      <OAuthSignInButtons />
    </KorakuAuthShell>
  );
}
