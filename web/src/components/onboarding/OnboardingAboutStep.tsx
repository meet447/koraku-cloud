"use client";

import { useMemo } from "react";
import clsx from "clsx";
import {
  collectProfileLinks,
  MAX_CUSTOM_PROFILE_LINKS,
  type ProfileLinkFormState,
} from "@/lib/profile-links";
import { korakuUi } from "@/lib/koraku-ui";

type Props = {
  additionalInfo: string;
  helpWith: string[];
  profileLinksForm: ProfileLinkFormState;
  helpOptions: readonly string[];
  onPatch: (patch: {
    additionalInfo?: string;
    helpWith?: string[];
    profileLinksForm?: ProfileLinkFormState;
  }) => void;
};

function toggleChip(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

export function OnboardingAboutStep({
  additionalInfo,
  helpWith,
  profileLinksForm,
  helpOptions,
  onPatch,
}: Props) {
  const collectedLinks = useMemo(
    () => collectProfileLinks(profileLinksForm),
    [profileLinksForm],
  );

  function updateCustomLink(index: number, patch: Partial<{ label: string; url: string }>) {
    const next = profileLinksForm.customLinks.map((row, i) =>
      i === index ? { ...row, ...patch } : row,
    );
    onPatch({ profileLinksForm: { ...profileLinksForm, customLinks: next } });
  }

  function addCustomLink() {
    if (profileLinksForm.customLinks.length >= MAX_CUSTOM_PROFILE_LINKS) return;
    onPatch({
      profileLinksForm: {
        ...profileLinksForm,
        customLinks: [...profileLinksForm.customLinks, { label: "Portfolio", url: "" }],
      },
    });
  }

  function removeCustomLink(index: number) {
    onPatch({
      profileLinksForm: {
        ...profileLinksForm,
        customLinks: profileLinksForm.customLinks.filter((_, i) => i !== index),
      },
    });
  }

  return (
    <div className="space-y-8">
      <div className="space-y-4 rounded-2xl border border-neutral-200/80 bg-neutral-50/60 p-5 sm:p-6">
        <p className={korakuUi.fieldLabel}>Public links (optional)</p>
        <p className="text-xs font-medium text-koraku-muted">
          LinkedIn, X, or up to three custom links. Koraku reads public pages when you continue.
        </p>
        <label className="block">
          <span className="text-xs font-semibold text-neutral-600">LinkedIn</span>
          <input
            value={profileLinksForm.linkedinUrl}
            onChange={(e) =>
              onPatch({
                profileLinksForm: { ...profileLinksForm, linkedinUrl: e.target.value },
              })
            }
            placeholder="linkedin.com/in/you"
            className={clsx(korakuUi.input, "mt-2")}
          />
        </label>
        <label className="block">
          <span className="text-xs font-semibold text-neutral-600">X (Twitter)</span>
          <input
            value={profileLinksForm.xUrl}
            onChange={(e) =>
              onPatch({ profileLinksForm: { ...profileLinksForm, xUrl: e.target.value } })
            }
            placeholder="x.com/you"
            className={clsx(korakuUi.input, "mt-2")}
          />
        </label>
        <div className="space-y-3">
          <span className="text-xs font-semibold text-neutral-600">Other links</span>
          {profileLinksForm.customLinks.map((row, index) => (
            <div
              key={`custom-link-${index}`}
              className="grid gap-2 sm:grid-cols-[minmax(8rem,10rem)_1fr_auto]"
            >
              <input
                value={row.label}
                onChange={(e) => updateCustomLink(index, { label: e.target.value })}
                placeholder="Label"
                className={korakuUi.input}
              />
              <input
                value={row.url}
                onChange={(e) => updateCustomLink(index, { url: e.target.value })}
                placeholder="yoursite.com"
                className={korakuUi.input}
              />
              <button
                type="button"
                onClick={() => removeCustomLink(index)}
                className="rounded-xl px-3 text-sm font-semibold text-neutral-500 hover:bg-white hover:text-neutral-900"
              >
                Remove
              </button>
            </div>
          ))}
          {profileLinksForm.customLinks.length < MAX_CUSTOM_PROFILE_LINKS ? (
            <button
              type="button"
              onClick={addCustomLink}
              className="text-sm font-semibold text-orange-700 hover:text-orange-800"
            >
              + Add link
            </button>
          ) : null}
        </div>
        {collectedLinks.length > 0 ? (
          <p className="text-xs font-medium text-koraku-muted">
            {collectedLinks.length} link{collectedLinks.length === 1 ? "" : "s"} will be used
          </p>
        ) : null}
      </div>

      <label className="block">
        <span className={korakuUi.fieldLabel}>Additional info (optional)</span>
        <p className="mt-1 text-xs font-medium text-koraku-muted">
          Role, projects, interests, or anything else Koraku should know.
        </p>
        <textarea
          value={additionalInfo}
          onChange={(e) => onPatch({ additionalInfo: e.target.value })}
          rows={4}
          placeholder="I'm a product lead at a climate startup. I focus on roadmap planning, user research, and async team updates…"
          className={clsx(korakuUi.textarea, "mt-3")}
        />
      </label>

      <div>
        <p className={korakuUi.fieldLabel}>Koraku should help me with</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {helpOptions.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => onPatch({ helpWith: toggleChip(helpWith, item) })}
              className={clsx(
                "rounded-full px-4 py-2 text-sm font-semibold ring-1 transition",
                helpWith.includes(item)
                  ? "bg-neutral-950 text-white ring-neutral-950"
                  : "bg-white text-neutral-700 ring-neutral-200 hover:bg-neutral-50",
              )}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      <p className="text-sm font-medium text-koraku-muted">
        Click <span className="font-semibold text-koraku-ink">Next</span> and Koraku will draft your
        profile from what you shared.
      </p>
    </div>
  );
}
