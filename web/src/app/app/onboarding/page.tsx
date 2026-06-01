"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { APP_BASE } from "@/lib/app-path";

const helperOptions = [
  "Remember my preferences and context",
  "Organize notes, plans, and decisions",
  "Research and summarize things for me",
  "Automate recurring personal admin",
  "Help me follow through on tasks",
];

const appOptions = ["Gmail", "Google Calendar", "Google Drive", "Slack", "Notion", "Linear"];

export default function OnboardingPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [tone, setTone] = useState("Concise, warm, and practical");
  const [goals, setGoals] = useState<string[]>(["Remember my preferences and context"]);
  const [apps, setApps] = useState<string[]>(["Gmail", "Google Calendar"]);
  const [automationIdea, setAutomationIdea] = useState("Give me a weekday morning brief from my calendar and inbox.");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem("koraku_onboarding_done");
      if (stored === "1") return;
    } catch {
      /* ignore */
    }
  }, []);

  function toggle(list: string[], value: string, setter: (next: string[]) => void) {
    setter(list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);
  }

  async function save() {
    setSaving(true);
    setError(null);
    const memory = [
      "## Onboarding profile",
      name.trim() ? `- User name: ${name.trim()}` : "",
      goals.length ? `- Koraku should help with: ${goals.join(", ")}` : "",
      apps.length ? `- Important connected apps to set up: ${apps.join(", ")}` : "",
      automationIdea.trim() ? `- First automation idea: ${automationIdea.trim()}` : "",
      "- When suggesting external actions, verify the target app/account and ask for confirmation before sending or changing data.",
    ]
      .filter(Boolean)
      .join("\n");
    const starterPrompts = [
      "Remember that I want Koraku to help with: " + goals.join(", "),
      "Create a second-brain note for my current priorities.",
      automationIdea.trim()
        ? `Turn this into a safe automation plan: ${automationIdea.trim()}`
        : "Suggest three useful starter automations for me.",
    ];
    try {
      const r = await fetch("/koraku-api/api/personalization", {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agent_name: "Koraku",
          memory,
          soul: tone.trim(),
        }),
      });
      if (!r.ok) throw new Error(`Save failed (${r.status})`);
      window.localStorage.setItem("koraku_onboarding_done", "1");
      window.localStorage.setItem("koraku_starter_prompts", JSON.stringify(starterPrompts));
      router.push(APP_BASE);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save onboarding");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="min-h-0 flex-1 overflow-y-auto bg-[#fbfaf6] px-6 py-10">
      <div className="mx-auto max-w-4xl">
        <p className="mb-4 text-xs font-bold uppercase tracking-[0.22em] text-orange-700">
          First run
        </p>
        <h1 className="text-4xl font-bold tracking-tight text-neutral-950">
          Teach Koraku how to be useful from day one.
        </h1>
        <p className="mt-3 max-w-2xl text-[15px] font-medium leading-relaxed text-neutral-600">
          These answers become your initial memory and persona. You can edit them
          later from Personalization.
        </p>

        {error ? (
          <p className="mt-6 rounded-2xl bg-red-50 px-4 py-3 text-sm font-semibold text-red-800 ring-1 ring-red-200">
            {error}
          </p>
        ) : null}

        <div className="mt-8 grid gap-5 lg:grid-cols-[1fr_0.85fr]">
          <section className="space-y-5 rounded-[32px] bg-white p-6 shadow-sm ring-1 ring-neutral-200/80">
            <label className="block">
              <span className="text-sm font-bold text-neutral-900">What should Koraku call you?</span>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                className="mt-3 w-full rounded-2xl border border-neutral-200 px-4 py-3 text-sm font-semibold outline-none focus:ring-2 focus:ring-orange-200"
              />
            </label>

            <div>
              <p className="text-sm font-bold text-neutral-900">What should Koraku help with?</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {helperOptions.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => toggle(goals, item, setGoals)}
                    className={`rounded-full px-4 py-2 text-sm font-semibold ring-1 transition ${
                      goals.includes(item)
                        ? "bg-neutral-950 text-white ring-neutral-950"
                        : "bg-white text-neutral-700 ring-neutral-200 hover:bg-neutral-50"
                    }`}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>

            <label className="block">
              <span className="text-sm font-bold text-neutral-900">Preferred companion style</span>
              <textarea
                value={tone}
                onChange={(e) => setTone(e.target.value)}
                rows={3}
                className="mt-3 w-full resize-y rounded-2xl border border-neutral-200 px-4 py-3 text-sm font-semibold leading-relaxed outline-none focus:ring-2 focus:ring-orange-200"
              />
            </label>
          </section>

          <section className="space-y-5 rounded-[32px] bg-neutral-950 p-6 text-white shadow-sm">
            <div>
              <p className="text-sm font-bold">Apps you may connect</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {appOptions.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => toggle(apps, item, setApps)}
                    className={`rounded-full px-4 py-2 text-sm font-semibold ring-1 transition ${
                      apps.includes(item)
                        ? "bg-white text-neutral-950 ring-white"
                        : "bg-white/5 text-white ring-white/15 hover:bg-white/10"
                    }`}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>

            <label className="block">
              <span className="text-sm font-bold">First automation idea</span>
              <textarea
                value={automationIdea}
                onChange={(e) => setAutomationIdea(e.target.value)}
                rows={6}
                className="mt-3 w-full resize-y rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-sm font-semibold leading-relaxed text-white outline-none placeholder:text-white/40 focus:ring-2 focus:ring-white/30"
              />
            </label>

            <button
              type="button"
              onClick={() => void save()}
              disabled={saving}
              className="w-full rounded-full bg-orange-300 px-6 py-3 text-sm font-bold text-neutral-950 transition hover:bg-orange-200 disabled:opacity-60"
            >
              {saving ? "Saving..." : "Start with Koraku"}
            </button>
          </section>
        </div>
      </div>
    </main>
  );
}
