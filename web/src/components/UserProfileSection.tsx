"use client";

import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import { errorMessage } from "@/lib/error-message";
import {
  loadPersonalization,
  savePersonalization,
} from "@/lib/koraku-personalization";
import {
  buildMemoryFromSections,
  emptyUserProfile,
  parseMemorySections,
  type UserProfileFields,
} from "@/lib/personalization-memory";
import { ONBOARDING_HELP_OPTIONS } from "@/lib/onboarding";
import { korakuUi } from "@/lib/koraku-ui";
import { KorakuAlert } from "@/components/KorakuAlert";
import { KorakuButton } from "@/components/KorakuButton";

function toggleChip(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

export function UserProfileSection({ embedded = false }: { embedded?: boolean }) {
  const [profile, setProfile] = useState<UserProfileFields>(emptyUserProfile);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const data = await loadPersonalization();
      setProfile(parseMemorySections(data.memory).profile);
    } catch (e) {
      setError(errorMessage(e, "Load failed"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function onSave() {
    setError(null);
    setSaving(true);
    setSavedAt(null);
    try {
      const current = await loadPersonalization();
      const { preferences } = parseMemorySections(current.memory);
      await savePersonalization({
        agent_name: current.agent_name,
        soul: current.soul,
        memory: buildMemoryFromSections(profile, preferences),
      });
      setSavedAt(Date.now());
    } catch (e) {
      setError(errorMessage(e, "Save failed"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section
      id="your-profile"
      className={clsx(embedded ? "scroll-mt-2" : [korakuUi.card, "scroll-mt-6"])}
    >
      <h2 className="text-lg font-bold text-koraku-ink">Your profile</h2>
      <p className="mt-2 text-sm font-medium leading-relaxed text-koraku-muted">
        What you shared during onboarding — your name, background, and how you want Koraku to help.
        This is stored in your account memory and used in every chat.
      </p>

      {error ? (
        <KorakuAlert variant="error" className="mt-4">
          {error}
        </KorakuAlert>
      ) : null}

      <div className="mt-6 space-y-5">
        <div className={korakuUi.cardPanel}>
          <label className={korakuUi.fieldLabel}>Your name</label>
          <input
            type="text"
            value={profile.userName}
            onChange={(e) => setProfile((p) => ({ ...p, userName: e.target.value }))}
            placeholder="Your name"
            disabled={loading}
            className={clsx(korakuUi.input, "mt-3")}
            maxLength={120}
            autoComplete="name"
          />
        </div>

        <div className={korakuUi.cardPanel}>
          <label className={korakuUi.fieldLabel}>About you</label>
          <textarea
            value={profile.about}
            onChange={(e) => setProfile((p) => ({ ...p, about: e.target.value }))}
            placeholder="What you do, your role, and context Koraku should remember…"
            disabled={loading}
            rows={5}
            className={clsx(korakuUi.textarea, "mt-3")}
          />
        </div>

        <div className={korakuUi.cardPanel}>
          <p className={korakuUi.fieldLabel}>Koraku should help me with</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {ONBOARDING_HELP_OPTIONS.map((item) => (
              <button
                key={item}
                type="button"
                disabled={loading}
                onClick={() =>
                  setProfile((p) => ({
                    ...p,
                    helpWith: toggleChip(p.helpWith, item),
                  }))
                }
                className={clsx(
                  "rounded-full px-4 py-2 text-sm font-semibold ring-1 transition disabled:opacity-50",
                  profile.helpWith.includes(item)
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

      <div className="mt-6 flex flex-wrap items-center justify-end gap-3">
        {savedAt ? (
          <span className="text-xs font-medium text-koraku-muted">Saved</span>
        ) : null}
        <KorakuButton onClick={() => void onSave()} disabled={loading || saving} className="px-8">
          {saving ? "Saving…" : "Save profile"}
        </KorakuButton>
      </div>
    </section>
  );
}
