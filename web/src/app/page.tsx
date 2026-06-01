import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";
import { APP_BASE } from "@/lib/app-path";
import { isSupabaseConfigured } from "@/lib/supabase/is-configured";

export default function LandingPage() {
  const supabaseConfigured = isSupabaseConfigured();
  const examples = [
    "Remember how I like to work, write, plan, and decide.",
    "Turn notes, chats, and files into a searchable second brain.",
    "Automate recurring life admin across connected apps.",
  ];

  return (
    <main className="relative min-h-dvh overflow-hidden bg-[#fbfaf6] text-koraku-ink">
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.45]"
        aria-hidden
        style={{
          backgroundImage:
            "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(251, 146, 60, 0.18), transparent), radial-gradient(ellipse 60% 40% at 100% 0%, rgba(253, 186, 116, 0.12), transparent)",
        }}
      />
      <div className="pointer-events-none absolute inset-x-0 top-24 mx-auto h-72 max-w-4xl rounded-full bg-orange-100/50 blur-3xl" />
      <div className="relative mx-auto flex min-h-dvh max-w-5xl flex-col px-6 py-16">
        <header className="mb-12 flex flex-col items-center text-center">
          <div className="mb-6 flex justify-center">
            <BrandMark size={80} priority />
          </div>
          <p className="mb-4 rounded-full border border-orange-200/70 bg-white/70 px-4 py-1.5 text-xs font-bold uppercase tracking-[0.24em] text-orange-700 shadow-sm">
            Public beta
          </p>
          <h1 className="mb-3 text-4xl font-bold tracking-tight text-neutral-900 sm:text-5xl">
            Your companion for memory, action, and everyday momentum.
          </h1>
          <p className="max-w-2xl text-lg leading-relaxed text-neutral-600">
            Koraku is a personal AI buddy that remembers your preferences, helps
            organize your second brain, and turns repeatable work into safe automations.
          </p>
        </header>

        <section className="mx-auto mb-10 grid w-full max-w-4xl gap-3 md:grid-cols-3">
          {examples.map((text, i) => (
            <article
              key={text}
              className="rounded-[28px] border border-white bg-white/80 p-5 shadow-[0_24px_70px_-40px_rgb(0_0_0_/_0.35)] ring-1 ring-neutral-200/70"
            >
              <p className="mb-4 text-xs font-bold uppercase tracking-[0.2em] text-neutral-400">
                0{i + 1}
              </p>
              <p className="text-[15px] font-semibold leading-relaxed text-neutral-800">
                {text}
              </p>
            </article>
          ))}
        </section>

        <div className="mx-auto flex w-full max-w-md flex-col gap-3 sm:flex-row sm:justify-center">
          <Link
            href={`${APP_BASE}`}
            className="inline-flex h-12 items-center justify-center rounded-full bg-koraku-ink px-8 text-sm font-semibold text-white shadow-sm transition hover:opacity-90"
          >
            Open app
          </Link>
          <Link
            href="/sign-in"
            className="inline-flex h-12 items-center justify-center rounded-full border border-neutral-300 bg-white px-8 text-sm font-semibold text-neutral-800 shadow-sm transition hover:bg-neutral-50"
          >
            Sign in
          </Link>
        </div>

        <p className="mt-8 text-center text-sm text-neutral-500">
          {supabaseConfigured ? (
            <>
              New here?{" "}
              <Link href="/sign-up?next=/app/onboarding" className="font-medium text-koraku-accent underline">
                Create an account
              </Link>
            </>
          ) : (
            <>
              Running locally without Supabase?{" "}
              <Link href={APP_BASE} className="font-medium text-koraku-accent underline">
                Open the app directly
              </Link>
              {" "}— set <code className="text-neutral-600">REQUIRE_AUTH_FOR_CHAT=false</code> on the API.
            </>
          )}
        </p>

        <p className="mx-auto mt-8 max-w-2xl rounded-3xl border border-orange-200/70 bg-white/70 px-5 py-4 text-center text-sm font-medium leading-relaxed text-neutral-600">
          Beta note: Koraku can draft, organize, research, and prepare actions. It
          will ask for confirmation before high-impact external actions like sending
          messages, creating calendar events, sharing files, or deleting data.
        </p>

        <footer className="mt-auto flex flex-wrap justify-center gap-x-4 gap-y-2 pt-16 text-center text-xs text-neutral-400">
          <span>
            {supabaseConfigured
              ? `The app requires sign-in. You will be redirected from ${APP_BASE} if you are not signed in.`
              : "Local demo mode: configure the API (.env) and open the app without an account."}
          </span>
          <Link href="/privacy" className="font-semibold text-neutral-500 underline">
            Privacy
          </Link>
          <Link href="/terms" className="font-semibold text-neutral-500 underline">
            Terms
          </Link>
        </footer>
      </div>
    </main>
  );
}
