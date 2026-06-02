"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { APP_BASE } from "@/lib/app-path";
import { errorMessage } from "@/lib/error-message";
import { savePersonalization } from "@/lib/koraku-personalization";
import { KorakuAppPage } from "@/components/KorakuAppPage";
import { KorakuPageHeader } from "@/components/KorakuPageHeader";
import { KorakuAlert } from "@/components/KorakuAlert";
import { KorakuButton } from "@/components/KorakuButton";

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
      "What do you already know about me from my profile?",
      automationIdea.trim()
        ? `Turn this into a safe automation plan: ${automationIdea.trim()}`
        : "Suggest three useful starter automations for me.",
    ];
    try {
      await savePersonalization({
        agent_name: "Koraku",
        memory,
        soul: tone.trim(),
      });
      window.localStorage.setItem("koraku_onboarding_done", "1");
      window.localStorage.setItem("koraku_starter_prompts", JSON.stringify(starterPrompts));
      router.push(APP_BASE);
    } catch (e) {
      setError(errorMessage(e, "Could not save onboarding"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <KorakuAppPage maxWidth="4xl">
        <KorakuPageHeader
          eyebrow="First run"
          title="Teach Koraku how to be useful from day one"
          description="These answers become your initial memory and persona. You can edit them later in Settings."
        />

        {error ? (
          <KorakuAlert variant="error" className="mt-6">
            {error}
          </KorakuAlert>
        ) : null}

        <div className="mt-8 grid gap-5 lg:grid-cols-[1fr_0.85fr]">
          <section className="space-y-5 rounded-[32px] bg-white p-6 shadow-sm ring-1 ring-neutral-200/80">
            <label className="block">
              <span className="text-sm font-bold text-koraku-ink">What should Koraku call you?</span>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                className="mt-3 w-full rounded-2xl border border-neutral-200 px-4 py-3 text-sm font-semibold outline-none focus:ring-2 focus:ring-orange-200"
              />
            </label>

            <div>
              <p className="text-sm font-bold text-koraku-ink">What should Koraku help with?</p>
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
              <span className="text-sm font-bold text-koraku-ink">Preferred companion style</span>
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

            <KorakuButton
              fullWidth
              onClick={() => void save()}
              disabled={saving}
              className="bg-orange-300 text-koraku-ink hover:bg-orange-200 disabled:opacity-60"
            >
              {saving ? "Saving..." : "Start with Koraku"}
            </KorakuButton>
          </section>
        </div>
    </KorakuAppPage>
  );
}
