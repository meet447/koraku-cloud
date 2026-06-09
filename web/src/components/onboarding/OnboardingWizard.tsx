"use client";

import { useCallback, useEffect, useRef, useState } from "react";
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
  shouldAutoGenerateAboutOnNext,
  isAboutProfileReady,
  resetAboutProfileFields,
  pendingProfileLinksForDisplay,
  linkSummariesFromResults,
  STARTER_PROMPTS_KEY,
  validateOnboardingStep,
  type OnboardingFormData,
  type OnboardingStepId,
} from "@/lib/onboarding";
import { parseMemorySections } from "@/lib/personalization-memory";
import { collectProfileLinks, profileLinksToFormState } from "@/lib/profile-links";
import { enrichProfileFromLinks } from "@/lib/profile-enrich";
import { revealTextIncrementally } from "@/lib/reveal-text";
import { korakuUi } from "@/lib/koraku-ui";
import { KorakuAppPage } from "@/components/KorakuAppPage";
import { KorakuAlert } from "@/components/KorakuAlert";
import { KorakuButton } from "@/components/KorakuButton";
import { OnboardingAboutStep } from "@/components/onboarding/OnboardingAboutStep";
import { OnboardingAboutGeneratedView } from "@/components/onboarding/OnboardingAboutGeneratedView";
import {
  OnboardingAboutGenerateView,
  type AboutGeneratePhase,
} from "@/components/onboarding/OnboardingAboutGenerateView";
import { OnboardingConnectionsStep } from "@/components/onboarding/OnboardingConnectionsStep";
import { OnboardingWizardSkeleton } from "@/components/onboarding/OnboardingSkeleton";
import type { ProfileLinkResult } from "@/lib/profile-links";

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
  const [aboutGenerating, setAboutGenerating] = useState(false);
  const [aboutGenerate, setAboutGenerate] = useState<{
    phase: AboutGeneratePhase;
    statusMessage: string;
    displayedAbout: string;
    pendingLinks: ReturnType<typeof pendingProfileLinksForDisplay>;
    linkResults: ProfileLinkResult[];
  } | null>(null);
  const aboutGenerateAbortRef = useRef<AbortController | null>(null);

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
          profileLinksForm: profile.profileLinks.length
            ? profileLinksToFormState(profile.profileLinks)
            : prev.profileLinksForm,
          linkSummaries: profile.linkSummaries.length ? profile.linkSummaries : prev.linkSummaries,
          aboutProfileReady: profile.about.trim() ? true : prev.aboutProfileReady,
          agentName: data.agent_name || prev.agentName,
          preferences: preferences || prev.preferences,
          persona: data.soul || prev.persona,
        }));
      })
      .catch(() => {})
      .finally(() => setHydrated(true));
  }, [initial.needsRemote]);

  useEffect(() => {
    return () => {
      aboutGenerateAbortRef.current?.abort();
    };
  }, []);

  function goBack() {
    if (aboutGenerating) {
      aboutGenerateAbortRef.current?.abort();
      setAboutGenerating(false);
      setAboutGenerate(null);
    }
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

  async function advanceFromAboutStep() {
    const err = validateOnboardingStep("about", form);
    if (err) {
      setStepError(err);
      return;
    }
    setStepError(null);

    if (isAboutProfileReady(form)) {
      goNext();
      return;
    }

    if (!shouldAutoGenerateAboutOnNext(form)) {
      goNext();
      return;
    }

    aboutGenerateAbortRef.current?.abort();
    const controller = new AbortController();
    aboutGenerateAbortRef.current = controller;

    const pendingLinks = pendingProfileLinksForDisplay(form);
    const hasLinks = pendingLinks.length > 0;
    setAboutGenerating(true);
    setAboutGenerate({
      phase: "fetching",
      statusMessage: hasLinks
        ? "Reading your public links…"
        : "Drafting from your notes…",
      displayedAbout: "",
      pendingLinks,
      linkResults: [],
    });

    try {
      const response = await enrichProfileFromLinks({
        userName: form.userName,
        existingAbout: form.about,
        additionalInfo: form.additionalInfo,
        helpWith: form.helpWith,
        links: collectProfileLinks(form.profileLinksForm),
      });
      if (controller.signal.aborted) return;

      setAboutGenerate((prev) =>
        prev
          ? {
              ...prev,
              statusMessage: "Drafting your profile…",
              linkResults: response.link_results,
            }
          : null,
      );

      await new Promise((resolve) => window.setTimeout(resolve, 500));
      if (controller.signal.aborted) return;

      const about = response.about.trim();
      if (!about) {
        setStepError("Could not generate a profile description. Write one manually or try again.");
        return;
      }
      setAboutGenerate((prev) =>
        prev
          ? {
              ...prev,
              phase: "writing",
              statusMessage: "Writing your description…",
            }
          : null,
      );

      await revealTextIncrementally(
        about,
        (partial) => {
          setAboutGenerate((prev) => (prev ? { ...prev, displayedAbout: partial } : null));
        },
        { charDelayMs: 12, chunkSize: 4, signal: controller.signal },
      );
      if (controller.signal.aborted) return;

      const summaries = linkSummariesFromResults(response.link_results);
      const nextForm: OnboardingFormData = {
        ...form,
        about,
        linkSummaries: summaries,
        aboutProfileReady: true,
      };

      setAboutGenerate((prev) =>
        prev
          ? {
              ...prev,
              phase: "complete",
              statusMessage: "Profile ready",
              displayedAbout: about,
            }
          : null,
      );

      await new Promise((resolve) => window.setTimeout(resolve, 700));
      if (controller.signal.aborted) return;

      setForm(nextForm);
      if (hydrated) saveOnboardingDraft(nextForm, stepIndex);
    } catch (e) {
      if (controller.signal.aborted) return;
      setStepError(errorMessage(e, "Could not build your profile from links"));
    } finally {
      if (!controller.signal.aborted) {
        setAboutGenerating(false);
        setAboutGenerate(null);
      }
    }
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

  function resetAboutProfile() {
    setStepError(null);
    patchForm(resetAboutProfileFields());
  }

  function handlePrimary() {
    if (isLast) {
      void finish();
      return;
    }
    if (stepId === "about") {
      void advanceFromAboutStep();
      return;
    }
    goNext();
  }

  if (!hydrated) {
    return (
      <KorakuAppPage maxWidth="5xl" className="py-8 sm:py-12">
        <OnboardingWizardSkeleton stepCount={ONBOARDING_STEPS.length} />
      </KorakuAppPage>
    );
  }

  return (
    <KorakuAppPage maxWidth="5xl" className="py-8 sm:py-12">
      <header className="mb-10">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-700">Welcome to Koraku</p>
        <div className="mt-5 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-koraku-muted">
              Step {stepIndex + 1} of {ONBOARDING_STEPS.length}
            </p>
            <h1 className="mt-1 text-3xl font-bold tracking-tight text-koraku-ink sm:text-4xl">
              {step.title}
            </h1>
          </div>
          <p className="max-w-sm text-sm font-medium leading-relaxed text-koraku-muted">
            {step.description}
          </p>
        </div>
        <div
          className="mt-6 flex gap-2"
          role="progressbar"
          aria-label={`Onboarding step ${stepIndex + 1} of ${ONBOARDING_STEPS.length}`}
          aria-valuenow={stepIndex + 1}
          aria-valuemin={1}
          aria-valuemax={ONBOARDING_STEPS.length}
        >
          {ONBOARDING_STEPS.map((s, i) => (
            <div key={s.id} className="min-w-0 flex-1">
              <div
                className={clsx(
                  "h-2 rounded-full transition-colors duration-300",
                  i <= stepIndex ? "bg-neutral-900" : "bg-neutral-200",
                )}
                aria-hidden
              />
              <p
                className={clsx(
                  "mt-2 hidden truncate text-[11px] font-semibold uppercase tracking-wide lg:block",
                  i === stepIndex ? "text-koraku-ink" : "text-neutral-400",
                )}
              >
                {s.title}
              </p>
            </div>
          ))}
        </div>
      </header>

      <section className={clsx(korakuUi.card, "min-h-[360px] p-6 sm:p-8")}>
        {saveError ? (
          <KorakuAlert variant="error" className="mb-5">
            {saveError}
          </KorakuAlert>
        ) : null}
        {stepError ? (
          <KorakuAlert variant="error" className="mb-5">
            {stepError}
          </KorakuAlert>
        ) : null}

        <div className={saveError || stepError ? undefined : "mt-1"}>
          {aboutGenerating && aboutGenerate ? (
            <OnboardingAboutGenerateView
              phase={aboutGenerate.phase}
              statusMessage={aboutGenerate.statusMessage}
              displayedAbout={aboutGenerate.displayedAbout}
              pendingLinks={aboutGenerate.pendingLinks}
              linkResults={aboutGenerate.linkResults}
            />
          ) : stepId === "about" && isAboutProfileReady(form) ? (
            <OnboardingAboutGeneratedView about={form.about} onStartOver={resetAboutProfile} />
          ) : (
            <StepFields stepId={stepId} form={form} patchForm={patchForm} saving={saving} />
          )}
        </div>
      </section>

      <footer className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-neutral-200/80 pt-6">
        <KorakuButton
          variant="secondary"
          onClick={goBack}
          disabled={isFirst || saving || aboutGenerating}
        >
          Back
        </KorakuButton>
        <div className="flex flex-wrap gap-3">
          <KorakuButton onClick={handlePrimary} disabled={saving || aboutGenerating}>
            {aboutGenerating
              ? "Building profile…"
              : saving
                ? "Saving…"
                : isLast
                  ? "Finish"
                  : stepId === "about" && !isAboutProfileReady(form)
                    ? "Next — build profile"
                    : "Next"}
          </KorakuButton>
        </div>
      </footer>
    </KorakuAppPage>
  );
}

function StepFields({
  stepId,
  form,
  patchForm,
  saving,
}: {
  stepId: OnboardingStepId;
  form: OnboardingFormData;
  patchForm: (patch: Partial<OnboardingFormData>) => void;
  saving: boolean;
}) {
  switch (stepId) {
    case "name":
      return (
        <label className="block max-w-2xl">
          <span className={korakuUi.fieldLabel}>Your name</span>
          <input
            value={form.userName}
            onChange={(e) => patchForm({ userName: e.target.value })}
            placeholder="Alex"
            className={clsx(korakuUi.input, "mt-3 text-base sm:text-lg")}
            maxLength={120}
            autoComplete="name"
          />
        </label>
      );

    case "about":
      if (isAboutProfileReady(form)) {
        return null;
      }
      return (
        <OnboardingAboutStep
          additionalInfo={form.additionalInfo}
          helpWith={form.helpWith}
          profileLinksForm={form.profileLinksForm}
          helpOptions={ONBOARDING_HELP_OPTIONS}
          onPatch={patchForm}
        />
      );

    case "agent-name":
      return (
        <label className="block max-w-2xl">
          <span className={korakuUi.fieldLabel}>Agent name</span>
          <input
            value={form.agentName}
            onChange={(e) => patchForm({ agentName: e.target.value })}
            placeholder="Koraku"
            className={clsx(korakuUi.input, "mt-3 text-base sm:text-lg")}
            maxLength={120}
          />
        </label>
      );

    case "preferences":
      return (
        <div className="max-w-3xl space-y-5">
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
        <div className="max-w-3xl space-y-5">
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
      return <OnboardingConnectionsStep disabled={saving} />;

    default:
      return null;
  }
}
