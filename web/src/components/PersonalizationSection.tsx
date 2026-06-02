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
import { korakuUi } from "@/lib/koraku-ui";
import { KorakuAlert } from "@/components/KorakuAlert";
import { KorakuButton } from "@/components/KorakuButton";

export function PersonalizationSection() {
  const [agentName, setAgentName] = useState("");
  const [memory, setMemory] = useState("");
  const [soul, setSoul] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  const applyPayload = useCallback((data: PersonalizationPayload) => {
    setAgentName(data.agent_name);
    setMemory(data.memory);
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
      await savePersonalization({ agent_name: agentName, memory, soul });
      setSavedAt(Date.now());
    } catch (e) {
      setError(errorMessage(e, "Save failed"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section id="personalization" className={clsx(korakuUi.card, "scroll-mt-6")}>
      <h2 className="text-lg font-bold text-koraku-ink">Personalization</h2>
      <p className="mt-2 text-sm font-medium leading-relaxed text-koraku-muted">
        Profile text injected into every chat: what to call the agent, standing preferences, and
        persona. Facts learned automatically across chats live under{" "}
        <Link href={`${APP_BASE}/memory`} className="font-semibold text-koraku-ink underline">
          Memory
        </Link>
        .
      </p>

      {error ? (
        <KorakuAlert variant="error" className="mt-4">
          {error}
        </KorakuAlert>
      ) : null}

      <div className="mt-6 space-y-5">
        <div className={korakuUi.cardPanel}>
          <label className={korakuUi.fieldLabel}>Agent name</label>
          <input
            type="text"
            value={agentName}
            onChange={(e) => setAgentName(e.target.value)}
            placeholder="Koraku"
            disabled={loading}
            className={clsx(korakuUi.input, "mt-3")}
            maxLength={120}
            autoComplete="off"
          />
        </div>

        <div className={korakuUi.cardPanel}>
          <label className={korakuUi.fieldLabel}>Preferences</label>
          <p className="mt-1 text-sm font-medium text-neutral-600">
            Standing instructions and stable facts you want in every conversation.
          </p>
          <textarea
            value={memory}
            onChange={(e) => setMemory(e.target.value)}
            placeholder={
              "- Prefer concise answers with clear next steps\n- Ask before sending email or changing calendars"
            }
            disabled={loading}
            rows={8}
            className={clsx(korakuUi.textarea, "mt-3")}
          />
        </div>

        <div className={korakuUi.cardPanel}>
          <label className={korakuUi.fieldLabel}>Persona</label>
          <p className="mt-1 text-sm font-medium text-neutral-600">
            Optional tone and style layered on top of base Koraku behavior.
          </p>
          <textarea
            value={soul}
            onChange={(e) => setSoul(e.target.value)}
            placeholder="e.g. warm mentor, direct and practical, no fluff"
            disabled={loading}
            rows={5}
            className={clsx(korakuUi.textarea, "mt-3")}
          />
        </div>
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-end gap-3">
        {savedAt ? (
          <span className="text-xs font-medium text-koraku-muted">Saved</span>
        ) : null}
        <KorakuButton onClick={() => void onSave()} disabled={loading || saving} className="px-8">
          {saving ? "Saving…" : "Save personalization"}
        </KorakuButton>
      </div>
    </section>
  );
}
