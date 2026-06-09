"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import clsx from "clsx";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { KorakuAlert } from "@/components/KorakuAlert";
import { KorakuButton } from "@/components/KorakuButton";
import { errorMessage } from "@/lib/error-message";
import {
  deleteSkill,
  loadSkills,
  normalizeSkillSlug,
  saveSkill,
  SKILL_BODY_PLACEHOLDER,
  type KorakuSkill,
} from "@/lib/koraku-skills";
import { korakuUi } from "@/lib/koraku-ui";

type EditorMode = "none" | "create" | "edit";

type SkillDraft = {
  slug: string;
  name: string;
  description: string;
  body: string;
  enabled: boolean;
};

const EMPTY_DRAFT: SkillDraft = {
  slug: "",
  name: "",
  description: "",
  body: "",
  enabled: true,
};

function skillToDraft(skill: KorakuSkill): SkillDraft {
  return {
    slug: skill.slug,
    name: skill.name,
    description: skill.description,
    body: skill.body,
    enabled: skill.enabled,
  };
}

function skillSummary(skill: KorakuSkill): string {
  const text = (skill.description || skill.body || "").trim();
  if (!text) return "No description yet";
  const oneLine = text.replace(/\s+/g, " ");
  return oneLine.length > 120 ? `${oneLine.slice(0, 117)}…` : oneLine;
}

export function SkillsSection() {
  const [items, setItems] = useState<KorakuSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [mode, setMode] = useState<EditorMode>("none");
  const [draft, setDraft] = useState<SkillDraft>(EMPTY_DRAFT);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const selectedSlug = mode === "edit" ? draft.slug : null;

  const sortedItems = useMemo(
    () => [...items].toSorted((a, b) => a.slug.localeCompare(b.slug)),
    [items],
  );

  const refresh = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      setItems(await loadSkills({ force: true }));
    } catch (e) {
      setError(errorMessage(e, "Could not load skills"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  function startCreate() {
    setError(null);
    setSavedAt(null);
    setMode("create");
    setDraft({ ...EMPTY_DRAFT, body: SKILL_BODY_PLACEHOLDER });
  }

  function startEdit(skill: KorakuSkill) {
    setError(null);
    setSavedAt(null);
    setMode("edit");
    setDraft(skillToDraft(skill));
  }

  function cancelEditor() {
    setMode("none");
    setDraft(EMPTY_DRAFT);
    setConfirmDelete(false);
  }

  async function onSave() {
    setError(null);
    setSaving(true);
    setSavedAt(null);
    try {
      const slug = normalizeSkillSlug(draft.slug);
      if (!draft.name.trim()) {
        throw new Error("Name is required.");
      }
      await saveSkill(slug, {
        name: draft.name.trim(),
        description: draft.description.trim(),
        body: draft.body,
        enabled: draft.enabled,
      });
      await refresh();
      setMode("edit");
      setDraft((prev) => ({ ...prev, slug }));
      setSavedAt(Date.now());
    } catch (e) {
      setError(errorMessage(e, "Save failed"));
    } finally {
      setSaving(false);
    }
  }

  async function onDelete() {
    setError(null);
    setDeleting(true);
    try {
      await deleteSkill(draft.slug);
      cancelEditor();
      await refresh();
    } catch (e) {
      setError(errorMessage(e, "Delete failed"));
    } finally {
      setDeleting(false);
      setConfirmDelete(false);
    }
  }

  const showEditor = mode !== "none";

  return (
    <section className={korakuUi.card}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-koraku-ink">Organization skills</h2>
          <p className="mt-1.5 max-w-2xl text-sm font-medium leading-snug text-koraku-muted">
            Markdown playbooks injected into the agent system prompt. Use a clear description so the
            agent knows when to follow each skill.
          </p>
        </div>
        <KorakuButton
          variant="secondary"
          size="sm"
          onClick={startCreate}
          disabled={loading || mode === "create"}
          className="shrink-0"
        >
          <Plus className="mr-1.5 h-4 w-4" aria-hidden />
          New skill
        </KorakuButton>
      </div>

      {error ? (
        <KorakuAlert variant="error" className="mt-4">
          {error}
        </KorakuAlert>
      ) : null}

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,14rem)_minmax(0,1fr)]">
        <div className="space-y-2">
          {loading ? (
            <div className="space-y-2">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="h-16 animate-pulse rounded-xl border border-neutral-200/80 bg-koraku-panel"
                />
              ))}
            </div>
          ) : sortedItems.length === 0 ? (
            <div className={clsx(korakuUi.cardPanel, "text-sm font-medium text-koraku-muted")}>
              No custom skills yet. Platform defaults still apply in chat.
            </div>
          ) : (
            sortedItems.map((skill) => {
              const active = selectedSlug === skill.slug;
              return (
                <button
                  key={skill.slug}
                  type="button"
                  onClick={() => startEdit(skill)}
                  className={clsx(
                    "w-full rounded-xl border px-3.5 py-3 text-left transition",
                    active
                      ? "border-neutral-300 bg-white shadow-sm ring-2 ring-neutral-200/80"
                      : "border-neutral-200/80 bg-koraku-panel hover:border-neutral-300 hover:bg-white",
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-sm font-semibold text-koraku-ink">
                      {skill.name.trim() || skill.slug}
                    </span>
                    <span
                      className={clsx(
                        "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
                        skill.enabled
                          ? "bg-emerald-50 text-emerald-800"
                          : "bg-neutral-100 text-neutral-500",
                      )}
                    >
                      {skill.enabled ? "On" : "Off"}
                    </span>
                  </div>
                  <p className="mt-1 font-mono text-[11px] text-neutral-500">{skill.slug}</p>
                  <p className="mt-1.5 text-xs font-medium leading-snug text-koraku-muted">
                    {skillSummary(skill)}
                  </p>
                </button>
              );
            })
          )}
        </div>

        {showEditor ? (
          <div className={clsx(korakuUi.cardPanel, "space-y-3")}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-bold text-koraku-ink">
                {mode === "create" ? "New skill" : "Edit skill"}
              </h3>
              <button
                type="button"
                onClick={cancelEditor}
                className="text-xs font-semibold text-koraku-muted underline-offset-2 hover:text-koraku-ink hover:underline"
              >
                Cancel
              </button>
            </div>

            {mode === "create" ? (
              <div>
                <label htmlFor="skill-slug" className={korakuUi.fieldLabel}>
                  Slug
                </label>
                <p className="mt-1 text-xs font-medium text-neutral-600">
                  Stable id (lowercase letters, digits, hyphens). Cannot be changed after saving.
                </p>
                <input
                  id="skill-slug"
                  type="text"
                  value={draft.slug}
                  onChange={(e) => setDraft((prev) => ({ ...prev, slug: e.target.value }))}
                  placeholder="weekly-report"
                  disabled={saving}
                  className={clsx(korakuUi.input, "mt-2 font-mono")}
                  autoComplete="off"
                />
              </div>
            ) : (
              <p className="font-mono text-xs font-medium text-neutral-500">{draft.slug}</p>
            )}

            <div>
              <label htmlFor="skill-name" className={korakuUi.fieldLabel}>
                Name
              </label>
              <input
                id="skill-name"
                type="text"
                value={draft.name}
                onChange={(e) => setDraft((prev) => ({ ...prev, name: e.target.value }))}
                placeholder="Weekly report"
                disabled={saving}
                maxLength={120}
                className={clsx(korakuUi.input, "mt-2")}
                autoComplete="off"
              />
            </div>

            <div>
              <label htmlFor="skill-description" className={korakuUi.fieldLabel}>
                Description
              </label>
              <p className="mt-1 text-xs font-medium text-neutral-600">
                When should the agent use this skill? Shown in the skills index.
              </p>
              <input
                id="skill-description"
                type="text"
                value={draft.description}
                onChange={(e) => setDraft((prev) => ({ ...prev, description: e.target.value }))}
                placeholder="Use when drafting the user's weekly status update."
                disabled={saving}
                maxLength={1024}
                className={clsx(korakuUi.input, "mt-2")}
                autoComplete="off"
              />
            </div>

            <div>
              <label htmlFor="skill-body" className={korakuUi.fieldLabel}>
                Instructions
              </label>
              <p className="mt-1 text-xs font-medium text-neutral-600">
                Markdown body injected into the agent prompt (SKILL.md format).
              </p>
              <textarea
                id="skill-body"
                value={draft.body}
                onChange={(e) => setDraft((prev) => ({ ...prev, body: e.target.value }))}
                disabled={saving}
                rows={16}
                className={clsx(korakuUi.textarea, "mt-2 font-mono text-[13px]")}
              />
            </div>

            <label className="flex cursor-pointer items-center gap-2.5 text-sm font-medium text-koraku-ink">
              <input
                type="checkbox"
                checked={draft.enabled}
                onChange={(e) => setDraft((prev) => ({ ...prev, enabled: e.target.checked }))}
                disabled={saving}
                className="h-4 w-4 rounded border-neutral-300"
              />
              Enabled for this organization
            </label>

            <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
              {mode === "edit" ? (
                <KorakuButton
                  variant="destructive"
                  size="sm"
                  onClick={() => setConfirmDelete(true)}
                  disabled={saving || deleting}
                >
                  <Trash2 className="mr-1.5 h-4 w-4" aria-hidden />
                  Delete
                </KorakuButton>
              ) : (
                <span />
              )}
              <div className="flex items-center gap-3">
                {savedAt ? (
                  <span className="text-xs font-medium text-koraku-muted">Saved</span>
                ) : null}
                <KorakuButton onClick={() => void onSave()} disabled={saving} className="px-8">
                  {saving ? "Saving…" : "Save skill"}
                </KorakuButton>
              </div>
            </div>
          </div>
        ) : (
          <div
            className={clsx(
              korakuUi.cardPanel,
              "flex min-h-[12rem] items-center justify-center text-center text-sm font-medium text-koraku-muted",
            )}
          >
            Select a skill to edit, or create a new one.
          </div>
        )}
      </div>

      <ConfirmDialog
        open={confirmDelete}
        title="Delete skill?"
        message={`Remove “${draft.name.trim() || draft.slug}” from your organization? This cannot be undone.`}
        confirmLabel="Delete"
        destructive
        onConfirm={() => void onDelete()}
        onCancel={() => setConfirmDelete(false)}
      />
    </section>
  );
}
