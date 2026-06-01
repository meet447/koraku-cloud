import Link from "next/link";

export default function PrivacyPage() {
  return (
    <main className="mx-auto min-h-dvh max-w-3xl px-6 py-16">
      <p className="text-xs font-bold uppercase tracking-[0.22em] text-orange-700">
        Public beta
      </p>
      <h1 className="mt-2 text-4xl font-bold tracking-tight text-neutral-950">
        Privacy and data handling
      </h1>
      <div className="mt-8 space-y-5 text-sm font-medium leading-relaxed text-neutral-700">
        <p>
          Koraku stores chat history, personalization memory, automation definitions,
          and automation run history in Supabase when configured. Active chat sessions
          and detached run buffers may also live temporarily in backend memory.
        </p>
        <p>
          Prompts, messages, tool definitions, and tool results may be sent to the
          configured LLM provider. Connected app actions may be processed by Composio,
          and cloud workspace execution may use Blaxel sandboxes when enabled.
        </p>
        <p>
          Do not save secrets as memory. Koraku is designed to ask for confirmation
          before high-impact external actions such as sending messages, changing
          calendars, sharing files, purchases, deletes, or account changes.
        </p>
        <p>
          You can export and delete Koraku-owned app data from Settings. Full account
          deletion and third-party provider retention may require support/admin action
          during the beta.
        </p>
      </div>
      <Link href="/" className="mt-8 inline-flex text-sm font-bold text-orange-700 underline">
        Back home
      </Link>
    </main>
  );
}
