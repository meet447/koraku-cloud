import { errorMessage } from "@/lib/error-message";
import { supabaseAuthHeaders } from "@/lib/supabase/fetch-auth";

export type KorakuFetchInit = Omit<RequestInit, "body"> & {
  json?: unknown;
  body?: BodyInit | null;
};

/**
 * Same-origin fetch with session cookies and Supabase Bearer when available.
 * Use for `/api/*` and `/koraku-api/*` from client components.
 */
export async function korakuFetch(
  input: RequestInfo | URL,
  init: KorakuFetchInit = {},
): Promise<Response> {
  const { json, headers: initHeaders, ...rest } = init;
  const headers = new Headers(initHeaders);
  const auth = await supabaseAuthHeaders();
  for (const [key, value] of Object.entries(auth)) {
    if (value) {
      headers.set(key, value);
    }
  }
  if (json !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  return fetch(input, {
    cache: "no-store",
    credentials: "include",
    ...rest,
    headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });
}

export async function korakuFetchJson<T>(
  input: RequestInfo | URL,
  init: KorakuFetchInit = {},
): Promise<T> {
  const response = await korakuFetch(input, init);
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(text.trim() || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function korakuFetchOk(
  input: RequestInfo | URL,
  init: KorakuFetchInit = {},
): Promise<void> {
  const response = await korakuFetch(input, init);
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(text.trim() || `Request failed (${response.status})`);
  }
}

export { errorMessage };
