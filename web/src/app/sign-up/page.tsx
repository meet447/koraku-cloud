import Link from "next/link";
import { OAuthSignInButtons } from "@/components/OAuthSignInButtons";

export const dynamic = "force-dynamic";

export default function SignUpPage() {
  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6 py-16">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight text-koraku-ink">
        Create account
      </h1>
      <p className="mb-8 text-sm text-neutral-600">
        Sign in with Google or GitHub to create your Koraku account, then teach
        Koraku how to help you. Already have one?{" "}
        <Link href="/sign-in" className="text-koraku-accent underline">
          Sign in
        </Link>
      </p>
      <OAuthSignInButtons />
      <p className="mt-8 text-center text-sm text-neutral-500">
        <Link href="/" className="underline">
          Home
        </Link>
      </p>
    </main>
  );
}
