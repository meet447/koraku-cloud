import { korakuFetchJson, korakuFetchOk } from "@/lib/koraku-fetch";

export type PersonalizationPayload = {
  agent_name: string;
  memory: string;
  soul: string;
};

export async function loadPersonalization(): Promise<PersonalizationPayload> {
  const data = await korakuFetchJson<PersonalizationPayload>("/koraku-api/api/personalization");
  return {
    agent_name: data.agent_name ?? "",
    memory: data.memory ?? "",
    soul: data.soul ?? "",
  };
}

export async function savePersonalization(payload: PersonalizationPayload): Promise<void> {
  await korakuFetchOk("/koraku-api/api/personalization", {
    method: "PUT",
    json: payload,
  });
}
