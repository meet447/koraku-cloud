import Link from "next/link";
import { OAuthSignInButtons } from "@/components/OAuthSignInButtons";

export const dynamic = "force-dynamic";

export default function SignInPage() {
  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6 py-16">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight text-koraku-ink">
        Sign in
      </h1>
      <p className="mb-8 text-sm text-neutral-600">
        Use Google or GitHub (configure providers in your Supabase project). New
        accounts are created on first sign-in.{" "}
        <Link href="/sign-up" className="text-koraku-accent underline">
          Sign up
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
