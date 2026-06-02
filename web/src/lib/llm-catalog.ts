export type LandingLlmModel = {
  id: string;
  label: string;
  providerId: string;
  logoUrl?: string;
};

type ModelCatalogEntry = {
  id: string;
  logo_url?: string;
  label?: string;
};

type ProviderBlock = {
  id: string;
  label?: string;
  configured?: boolean;
  models?: string[];
  entries?: ModelCatalogEntry[];
};

export type ChatModelsResponse = {
  providers?: ProviderBlock[];
  models?: string[];
  active_provider?: string;
  default_model?: string;
};

/** Mirrors `koraku/llm/catalog.py` curated Fireworks models. */
export const LANDING_LLM_MODELS: LandingLlmModel[] = [
  {
    id: "accounts/fireworks/models/kimi-k2p6",
    label: "Kimi K2",
    providerId: "fireworks",
    logoUrl: "https://app.fireworks.ai/images/logos/moonshot-icon.svg",
  },
  {
    id: "accounts/fireworks/models/qwen3p6-plus",
    label: "Qwen3 6 Plus",
    providerId: "fireworks",
    logoUrl: "https://app.fireworks.ai/images/logos/qwen-icon.svg",
  },
  {
    id: "accounts/fireworks/models/minimax-m2p7",
    label: "MiniMax M2",
    providerId: "fireworks",
    logoUrl: "https://app.fireworks.ai/images/logos/minimax-icon.svg",
  },
  {
    id: "accounts/fireworks/models/glm-5p1",
    label: "GLM 5.1",
    providerId: "fireworks",
    logoUrl: "https://app.fireworks.ai/images/logos/z-ai.svg",
  },
];

const LANDING_MODEL_IDS = new Set(LANDING_LLM_MODELS.map((model) => model.id));

export function shortModelTitle(raw: string): string {
  const tail = raw.includes("/") ? (raw.split("/").pop() ?? raw) : raw;
  return tail
    .replace(/\.(gguf|safetensors)$/i, "")
    .replace(/[-_]+/g, " ")
    .replace(/\bp(\d+)\b/gi, ".$1")
    .replace(/\bk(\d+)\b/gi, " k$1")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function resolveModelLogo(model: Pick<LandingLlmModel, "logoUrl">): string | undefined {
  return model.logoUrl;
}

function parseFireworksModels(data: ChatModelsResponse): LandingLlmModel[] {
  const fireworksBlock = data.providers?.find((block) => block.id === "fireworks");
  if (!fireworksBlock) return [];

  const entries: ModelCatalogEntry[] = fireworksBlock.entries?.length
    ? fireworksBlock.entries
    : (fireworksBlock.models ?? []).map((id) => ({ id }));

  return entries
    .filter((row) => LANDING_MODEL_IDS.has(row.id))
    .map((row) => ({
      id: row.id,
      label: (row.label || "").trim() || shortModelTitle(row.id),
      providerId: "fireworks",
      logoUrl: row.logo_url,
    }));
}

function mergeWithStaticDefaults(live: LandingLlmModel[]): LandingLlmModel[] {
  return LANDING_LLM_MODELS.map((model) => {
    const match = live.find((item) => item.id === model.id);
    if (!match) return model;
    return {
      ...model,
      label: match.label || model.label,
      logoUrl: match.logoUrl || model.logoUrl,
    };
  });
}

export async function fetchLandingLlmModels(): Promise<LandingLlmModel[]> {
  try {
    const response = await fetch("/koraku-api/api/chat-models", { cache: "no-store" });
    if (!response.ok) return LANDING_LLM_MODELS;
    const data = (await response.json()) as ChatModelsResponse;
    const live = parseFireworksModels(data);
    return live.length ? mergeWithStaticDefaults(live) : LANDING_LLM_MODELS;
  } catch {
    return LANDING_LLM_MODELS;
  }
}
