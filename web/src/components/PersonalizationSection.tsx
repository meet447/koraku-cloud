"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import { APP_BASE } from "@/lib/app-path";
import { errorMessage } from "@/lib/error-message";
import {
  loadPersonalization,
  savePersonalization,
  type PersonalizationPayload,
} from "@/lib/koraku-personalization";
import {
  buildMemoryFromSections,
  parseMemorySections,
} from "@/lib/personalization-memory";
import { korakuUi } from "@/lib/koraku-ui";
import { KorakuAlert } from "@/components/KorakuAlert";
import { KorakuButton } from "@/components/KorakuButton";

export function PersonalizationSection({
  embedded = false,
  hideIntro = false,
}: {
  embedded?: boolean;
  hideIntro?: boolean;
}) {
  const [agentName, setAgentName] = useState("");
  const [memory, setMemory] = useState("");
  const [soul, setSoul] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  const applyPayload = useCallback((data: PersonalizationPayload) => {
    setAgentName(data.agent_name);
    setMemory(parseMemorySections(data.memory).preferences);
    setSoul(data.soul);
  }, []);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      applyPayload(await loadPersonalization());
    } catch (e) {
      setError(errorMessage(e, "Load failed"));
    } finally {
      setLoading(false);
    }
  }, [applyPayload]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onSave() {
    setError(null);
    setSaving(true);
    setSavedAt(null);
    try {
      const current = await loadPersonalization();
      const { profile } = parseMemorySections(current.memory);
      await savePersonalization({
        agent_name: agentName,
        soul,
        memory: buildMemoryFromSections(profile, memory),
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
      id="personalization"
      className={clsx(
        embedded ? "scroll-mt-2" : hideIntro ? korakuUi.card : [korakuUi.card, "scroll-mt-6"],
      )}
    >
      {hideIntro ? null : (
        <>
          <h2 className="text-base font-bold text-koraku-ink">Agent personalization</h2>
          <p className="mt-1.5 text-sm font-medium leading-snug text-koraku-muted">
            How your agent shows up in chat: display name, standing preferences, and persona. Facts
            learned automatically across chats live under{" "}
            <Link href={`${APP_BASE}/memory`} className="font-semibold text-koraku-ink underline">
              Memory
            </Link>
            .
          </p>
        </>
      )}

      {error ? (
        <KorakuAlert variant="error" className={hideIntro ? "mb-3" : "mt-4"}>
          {error}
        </KorakuAlert>
      ) : null}

      <div className={clsx(hideIntro ? "space-y-3" : "mt-4 space-y-3")}>
        <div className={korakuUi.cardPanel}>
          <label htmlFor="personalization-agent-name" className={korakuUi.fieldLabel}>
            Agent name
          </label>
          <input
            id="personalization-agent-name"
            type="text"
            value={agentName}
            onChange={(e) => setAgentName(e.target.value)}
            placeholder="Koraku"
            disabled={loading}
            className={clsx(korakuUi.input, "mt-2")}
            maxLength={120}
            autoComplete="off"
          />
        </div>

        <div className={korakuUi.cardPanel}>
          <label htmlFor="personalization-preferences" className={korakuUi.fieldLabel}>
            Preferences
          </label>
          <p id="personalization-preferences-hint" className="mt-1 text-sm font-medium text-neutral-600">
            Standing instructions and stable facts you want in every conversation.
          </p>
          <textarea
            id="personalization-preferences"
            aria-describedby="personalization-preferences-hint"
            value={memory}
            onChange={(e) => setMemory(e.target.value)}
            placeholder={
              "- Prefer concise answers with clear next steps\n- Ask before sending email or changing calendars"
            }
            disabled={loading}
            rows={8}
            className={clsx(korakuUi.textarea, "mt-2")}
          />
        </div>

        <div className={korakuUi.cardPanel}>
          <label htmlFor="personalization-persona" className={korakuUi.fieldLabel}>
            Persona
          </label>
          <p id="personalization-persona-hint" className="mt-1 text-sm font-medium text-neutral-600">
            Optional tone and style layered on top of base Koraku behavior.
          </p>
          <textarea
            id="personalization-persona"
            aria-describedby="personalization-persona-hint"
            value={soul}
            onChange={(e) => setSoul(e.target.value)}
            placeholder="e.g. warm mentor, direct and practical, no fluff"
            disabled={loading}
            rows={5}
            className={clsx(korakuUi.textarea, "mt-2")}
          />
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-end gap-3">
        {savedAt ? (
          <span className="text-xs font-medium text-koraku-muted">Saved</span>
        ) : null}
        <KorakuButton onClick={() => void onSave()} disabled={loading || saving} className="px-8">
          {saving ? "Saving…" : "Save agent settings"}
        </KorakuButton>
      </div>
    </section>
  );
}
