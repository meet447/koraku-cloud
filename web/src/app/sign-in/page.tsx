import Link from "next/link";
import { OAuthSignInButtons } from "@/components/OAuthSignInButtons";
import { KorakuAuthShell } from "@/components/KorakuAuthShell";

export const dynamic = "force-dynamic";

export default function SignInPage() {
  return (
    <KorakuAuthShell
      title="Sign in"
      description={
        <>
          Use Google or GitHub to sign in. New accounts are created on first sign-in.{" "}
          <Link href="/sign-up" className="font-semibold text-koraku-ink underline">
            Sign up
          </Link>
        </>
      }
    >
      <OAuthSignInButtons />
    </KorakuAuthShell>
  );
}
