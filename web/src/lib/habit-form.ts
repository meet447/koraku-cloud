export type ScheduleKind = "every_n_minutes" | "daily" | "weekdays" | "weekly" | "custom";

export type SchedulePresetLike = {
  kind?: string;
  every_n_minutes?: number;
  hour?: number;
  minute?: number;
  day_of_week?: number;
  cron_expression?: string;
};

export type HabitFormAutomation = {
  title: string;
  headline: string;
  natural_language_spec: string;
  trigger_mode: "scheduled" | "event";
  timezone?: string | null;
  cron_expression?: string | null;
  toolkits: string[];
  schedule_preset?: SchedulePresetLike | null;
  event_source?: "generic" | "composio";
  composio_trigger_slug?: string | null;
  event_display?: string | null;
};

export type HabitScheduleFields = {
  scheduleKind: ScheduleKind;
  scheduleEveryN: number;
  scheduleHour: number;
  scheduleMinute: number;
  scheduleDow: number;
  formCron: string;
  formTz: string;
};

export function buildSchedulePreset(
  kind: ScheduleKind,
  opts: { everyN: number; hour: number; minute: number; dayOfWeek: number; cron: string },
): Record<string, unknown> {
  if (kind === "custom") {
    return { kind: "custom", cron_expression: opts.cron.trim() };
  }
  if (kind === "every_n_minutes") {
    return { kind, every_n_minutes: opts.everyN };
  }
  if (kind === "weekly") {
    return { kind, hour: opts.hour, minute: opts.minute, day_of_week: opts.dayOfWeek };
  }
  return { kind, hour: opts.hour, minute: opts.minute };
}

function inferScheduleFromCron(cron: string): Omit<HabitScheduleFields, "formTz"> {
  const parts = cron.trim().split(/\s+/);
  if (parts.length !== 5) {
    return {
      scheduleKind: "custom",
      scheduleEveryN: 30,
      scheduleHour: 9,
      scheduleMinute: 0,
      scheduleDow: 5,
      formCron: cron || "0 9 * * *",
    };
  }
  const [minute, hour, , , dow] = parts;
  if (minute.startsWith("*/") && hour === "*" && dow === "*") {
    const n = Number.parseInt(minute.slice(2), 10);
    return {
      scheduleKind: "every_n_minutes",
      scheduleEveryN: Number.isFinite(n) ? n : 30,
      scheduleHour: 9,
      scheduleMinute: 0,
      scheduleDow: 5,
      formCron: cron,
    };
  }
  if (dow === "1-5" && /^\d+$/.test(minute) && /^\d+$/.test(hour)) {
    return {
      scheduleKind: "weekdays",
      scheduleEveryN: 30,
      scheduleHour: Number.parseInt(hour, 10),
      scheduleMinute: Number.parseInt(minute, 10),
      scheduleDow: 5,
      formCron: cron,
    };
  }
  if (/^\d+$/.test(dow) && /^\d+$/.test(minute) && /^\d+$/.test(hour)) {
    return {
      scheduleKind: "weekly",
      scheduleEveryN: 30,
      scheduleHour: Number.parseInt(hour, 10),
      scheduleMinute: Number.parseInt(minute, 10),
      scheduleDow: Number.parseInt(dow, 10),
      formCron: cron,
    };
  }
  if (dow === "*" && /^\d+$/.test(minute) && /^\d+$/.test(hour)) {
    return {
      scheduleKind: "daily",
      scheduleEveryN: 30,
      scheduleHour: Number.parseInt(hour, 10),
      scheduleMinute: Number.parseInt(minute, 10),
      scheduleDow: 5,
      formCron: cron,
    };
  }
  return {
    scheduleKind: "custom",
    scheduleEveryN: 30,
    scheduleHour: 9,
    scheduleMinute: 0,
    scheduleDow: 5,
    formCron: cron,
  };
}

export function scheduleFieldsFromHabit(a: HabitFormAutomation): HabitScheduleFields {
  const preset = a.schedule_preset;
  const tz = a.timezone?.trim() || "UTC";
  if (preset?.kind) {
    const kind = preset.kind as ScheduleKind;
    return {
      scheduleKind: kind,
      scheduleEveryN: Number(preset.every_n_minutes) || 30,
      scheduleHour: Number(preset.hour ?? 9),
      scheduleMinute: Number(preset.minute ?? 0),
      scheduleDow: Number(preset.day_of_week ?? 5),
      formCron: String(preset.cron_expression || a.cron_expression || "0 9 * * *"),
      formTz: tz,
    };
  }
  const fromCron = inferScheduleFromCron(a.cron_expression || "0 9 * * *");
  return { ...fromCron, formTz: tz };
}

export function habitToFormState(a: HabitFormAutomation) {
  const sched = scheduleFieldsFromHabit(a);
  return {
    formTitle: a.title,
    formHeadline: a.headline || "",
    formSpec: a.natural_language_spec,
    formToolkits: a.toolkits.join(", "),
    formTriggerMode: a.trigger_mode,
    formEventSource: (a.event_source || "composio") as "generic" | "composio",
    composioTriggerSlug: a.composio_trigger_slug || "",
    ...sched,
  };
}

export function defaultHabitFormState() {
  let tz = "UTC";
  try {
    tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    /* ignore */
  }
  return {
    formTitle: "",
    formHeadline: "",
    formSpec: "",
    formTz: tz,
    scheduleKind: "daily" as ScheduleKind,
    scheduleEveryN: 30,
    scheduleHour: 9,
    scheduleMinute: 0,
    scheduleDow: 5,
    formCron: "0 9 * * *",
    formToolkits: "",
    formTriggerMode: "scheduled" as const,
    formEventSource: "composio" as const,
    composioTriggerSlug: "",
  };
}
