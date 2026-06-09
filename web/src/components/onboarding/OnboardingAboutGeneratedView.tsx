"use client";

import { Check } from "lucide-react";
import { KorakuButton } from "@/components/KorakuButton";
import { korakuUi } from "@/lib/koraku-ui";

type Props = {
  about: string;
  onStartOver: () => void;
};

export function OnboardingAboutGeneratedView({ about, onStartOver }: Props) {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
            <Check className="h-4 w-4" aria-hidden />
          </div>
          <div>
            <p className="text-sm font-bold text-koraku-ink">Your profile is ready</p>
            <p className="text-xs font-medium text-koraku-muted">
              Saved for memory — click Next to continue or start over to edit your inputs.
            </p>
          </div>
        </div>
        <KorakuButton variant="secondary" onClick={onStartOver}>
          Start over
        </KorakuButton>
      </div>

      <div>
        <p className={korakuUi.fieldLabel}>Describe yourself</p>
        <div className="mt-3 rounded-xl border border-neutral-200/90 bg-neutral-50/50 px-4 py-3.5">
          <p className="whitespace-pre-wrap text-sm font-medium leading-relaxed text-koraku-ink">
            {about}
          </p>
        </div>
      </div>
    </div>
  );
}
