"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import clsx from "clsx";
import { APP_BASE } from "@/lib/app-path";
import { errorMessage } from "@/lib/error-message";
import { loadPersonalization, savePersonalization } from "@/lib/koraku-personalization";
import {
  buildPersonalizationFromOnboarding,
  buildStarterPrompts,
  defaultOnboardingFormData,
  loadOnboardingDraft,
  markOnboardingComplete,
  ONBOARDING_HELP_OPTIONS,
  ONBOARDING_PERSONA_SUGGESTIONS,
  ONBOARDING_PREFERENCE_SUGGESTIONS,
  ONBOARDING_STEP_IDS,
  ONBOARDING_STEPS,
  saveOnboardingDraft,
  STARTER_PROMPTS_KEY,
  validateOnboardingStep,
  type OnboardingFormData,
  type OnboardingStepId,
} from "@/lib/onboarding";
import { parseMemorySections } from "@/lib/personalization-memory";
import { korakuUi } from "@/lib/koraku-ui";
import { KorakuAppPage } from "@/components/KorakuAppPage";
import { KorakuAlert } from "@/components/KorakuAlert";
import { KorakuButton } from "@/components/KorakuButton";
import { OnboardingConnectionsStep } from "@/components/onboarding/OnboardingConnectionsStep";

function toggleChip(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

function readInitialOnboarding() {
  const draft = loadOnboardingDraft();
  if (draft) {
    const { stepIndex, ...form } = draft;
    return { form, stepIndex, hydrated: true, needsRemote: false as const };
  }
  return {
    form: defaultOnboardingFormData(),
    stepIndex: 0,
    hydrated: false,
    needsRemote: true as const,
  };
}

export function OnboardingWizard() {
  const router = useRouter();
  const [initial] = useState(readInitialOnboarding);
  const [stepIndex, setStepIndex] = useState(initial.stepIndex);
  const [form, setForm] = useState<OnboardingFormData>(initial.form);
  const [hydrated, setHydrated] = useState(initial.hydrated);
  const [stepError, setStepError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const step = ONBOARDING_STEPS[stepIndex];
  const stepId = step?.id ?? ONBOARDING_STEP_IDS[0];
  const isFirst = stepIndex === 0;
  const isLast = stepIndex === ONBOARDING_STEPS.length - 1;

  const patchForm = useCallback(
    (patch: Partial<OnboardingFormData>) => {
      setForm((prev) => {
        const next = { ...prev, ...patch };
        if (hydrated) saveOnboardingDraft(next, stepIndex);
        return next;
      });
    },
    [hydrated, stepIndex],
  );

  useEffect(() => {
    if (!initial.needsRemote) {
      setHydrated(true);
      return;
    }
    void loadPersonalization()
      .then((data) => {
        if (!data.agent_name && !data.memory && !data.soul) return;
        const { profile, preferences } = parseMemorySections(data.memory);
        setForm((prev) => ({
          ...prev,
          userName: profile.userName || prev.userName,
          about: profile.about || prev.about,
          helpWith: profile.helpWith.length ? profile.helpWith : prev.helpWith,
          agentName: data.agent_name || prev.agentName,
          preferences: preferences || prev.preferences,
          persona: data.soul || prev.persona,
        }));
      })
      .catch(() => {})
      .finally(() => setHydrated(true));
  }, [initial.needsRemote]);

  function goBack() {
    setStepError(null);
    setStepIndex((i) => {
      const next = Math.max(0, i - 1);
      if (hydrated) saveOnboardingDraft(form, next);
      return next;
    });
  }

  function goNext() {
    const err = validateOnboardingStep(stepId, form);
    if (err) {
      setStepError(err);
      return;
    }
    setStepError(null);
    setStepIndex((i) => {
      const next = Math.min(ONBOARDING_STEPS.length - 1, i + 1);
      if (hydrated) saveOnboardingDraft(form, next);
      return next;
    });
  }

  async function finish() {
    setSaveError(null);
    setSaving(true);
    try {
      const payload = buildPersonalizationFromOnboarding(form);
      await savePersonalization(payload);
      markOnboardingComplete();
      try {
        window.localStorage.setItem(
          STARTER_PROMPTS_KEY,
          JSON.stringify(buildStarterPrompts(form)),
        );
      } catch {
        /* ignore */
      }
      router.push(APP_BASE);
    } catch (e) {
      setSaveError(errorMessage(e, "Could not save your profile"));
    } finally {
      setSaving(false);
    }
  }

  function handlePrimary() {
    if (isLast) {
      void finish();
      return;
    }
    goNext();
  }

  if (!hydrated) {
    return (
      <KorakuAppPage maxWidth="2xl">
        <p className="text-sm font-medium text-koraku-muted">Loading…</p>
      </KorakuAppPage>
    );
  }

  return (
    <KorakuAppPage maxWidth="2xl" className="py-8 sm:py-12">
      <div className="mb-8">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-700">Welcome</p>
        <div className="mt-3 flex items-center justify-between gap-4">
          <p className="text-sm font-semibold text-koraku-muted">
            Step {stepIndex + 1} of {ONBOARDING_STEPS.length}
          </p>
          <p className="text-sm font-semibold text-koraku-ink">{step.title}</p>
        </div>
        <div className="mt-4 flex gap-1.5">
          {ONBOARDING_STEPS.map((s, i) => (
            <div
              key={s.id}
              className={clsx(
                "h-1.5 flex-1 rounded-full transition-colors",
                i <= stepIndex ? "bg-neutral-900" : "bg-neutral-200",
              )}
              aria-hidden
            />
          ))}
        </div>
      </div>

      <section className={clsx(korakuUi.card, "min-h-[320px]")}>
        <h1 className="text-2xl font-bold tracking-tight text-koraku-ink">{step.title}</h1>
        <p className="mt-2 text-sm font-medium leading-relaxed text-koraku-muted">{step.description}</p>

        {saveError ? (
          <KorakuAlert variant="error" className="mt-5">
            {saveError}
          </KorakuAlert>
        ) : null}
        {stepError ? (
          <KorakuAlert variant="error" className="mt-5">
            {stepError}
          </KorakuAlert>
        ) : null}

        <div className="mt-8">
          <StepFields stepId={stepId} form={form} patchForm={patchForm} />
        </div>
      </section>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <KorakuButton variant="secondary" onClick={goBack} disabled={isFirst || saving}>
          Back
        </KorakuButton>
        <div className="flex flex-wrap gap-3">
          {isLast ? (
            <KorakuButton variant="secondary" onClick={() => void finish()} disabled={saving}>
              Skip for now
            </KorakuButton>
          ) : null}
          <KorakuButton onClick={handlePrimary} disabled={saving}>
            {saving ? "Saving…" : isLast ? "Finish" : "Next"}
          </KorakuButton>
        </div>
      </div>
    </KorakuAppPage>
  );
}

function StepFields({
  stepId,
  form,
  patchForm,
}: {
  stepId: OnboardingStepId;
  form: OnboardingFormData;
  patchForm: (patch: Partial<OnboardingFormData>) => void;
}) {
  switch (stepId) {
    case "name":
      return (
        <label className="block">
          <span className={korakuUi.fieldLabel}>Your name</span>
          <input
            value={form.userName}
            onChange={(e) => patchForm({ userName: e.target.value })}
            placeholder="Alex"
            className={clsx(korakuUi.input, "mt-3")}
            maxLength={120}
            autoComplete="name"
          />
        </label>
      );

    case "about":
      return (
        <div className="space-y-6">
          <label className="block">
            <span className={korakuUi.fieldLabel}>Describe yourself</span>
            <textarea
              value={form.about}
              onChange={(e) => patchForm({ about: e.target.value })}
              rows={5}
              placeholder="I'm a product lead at a startup. I juggle email, Notion docs, and weekly planning…"
              className={clsx(korakuUi.textarea, "mt-3")}
            />
          </label>
          <div>
            <p className={korakuUi.fieldLabel}>Koraku should help me with</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {ONBOARDING_HELP_OPTIONS.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => patchForm({ helpWith: toggleChip(form.helpWith, item) })}
                  className={clsx(
                    "rounded-full px-4 py-2 text-sm font-semibold ring-1 transition",
                    form.helpWith.includes(item)
                      ? "bg-neutral-950 text-white ring-neutral-950"
                      : "bg-white text-neutral-700 ring-neutral-200 hover:bg-neutral-50",
                  )}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        </div>
      );

    case "agent-name":
      return (
        <label className="block">
          <span className={korakuUi.fieldLabel}>Agent name</span>
          <input
            value={form.agentName}
            onChange={(e) => patchForm({ agentName: e.target.value })}
            placeholder="Koraku"
            className={clsx(korakuUi.input, "mt-3")}
            maxLength={120}
          />
        </label>
      );

    case "preferences":
      return (
        <div className="space-y-5">
          <div className="flex flex-wrap gap-2">
            {ONBOARDING_PREFERENCE_SUGGESTIONS.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => patchForm({ preferences: item })}
                className={clsx(
                  "rounded-full px-3 py-1.5 text-xs font-semibold ring-1 transition",
                  form.preferences === item
                    ? "bg-orange-100 text-orange-950 ring-orange-200"
                    : "bg-white text-neutral-600 ring-neutral-200 hover:bg-neutral-50",
                )}
              >
                {item}
              </button>
            ))}
          </div>
          <label className="block">
            <span className={korakuUi.fieldLabel}>Preferences (memory)</span>
            <textarea
              value={form.preferences}
              onChange={(e) => patchForm({ preferences: e.target.value })}
              rows={8}
              className={clsx(korakuUi.textarea, "mt-3")}
            />
          </label>
        </div>
      );

    case "persona":
      return (
        <div className="space-y-5">
          <div className="flex flex-wrap gap-2">
            {ONBOARDING_PERSONA_SUGGESTIONS.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => patchForm({ persona: item })}
                className={clsx(
                  "rounded-full px-3 py-1.5 text-xs font-semibold ring-1 transition",
                  form.persona === item
                    ? "bg-orange-100 text-orange-950 ring-orange-200"
                    : "bg-white text-neutral-600 ring-neutral-200 hover:bg-neutral-50",
                )}
              >
                {item}
              </button>
            ))}
          </div>
          <label className="block">
            <span className={korakuUi.fieldLabel}>Persona (soul)</span>
            <textarea
              value={form.persona}
              onChange={(e) => patchForm({ persona: e.target.value })}
              rows={6}
              placeholder="e.g. warm mentor, direct and practical"
              className={clsx(korakuUi.textarea, "mt-3")}
            />
          </label>
        </div>
      );

    case "connections":
      return <OnboardingConnectionsStep />;

    default:
      return null;
  }
}
