function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  if (signal?.aborted) return Promise.resolve();
  return new Promise((resolve) => {
    const timer = window.setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        window.clearTimeout(timer);
        resolve();
      },
      { once: true },
    );
  });
}

/** Reveal text in small chunks for a typewriter-style UI. */
export async function revealTextIncrementally(
  text: string,
  onUpdate: (partial: string) => void,
  options?: { charDelayMs?: number; chunkSize?: number; signal?: AbortSignal },
): Promise<void> {
  const delay = options?.charDelayMs ?? 14;
  const chunk = Math.max(1, options?.chunkSize ?? 3);
  const signal = options?.signal;

  for (let i = 0; i < text.length; i += chunk) {
    if (signal?.aborted) return;
    onUpdate(text.slice(0, Math.min(i + chunk, text.length)));
    await sleep(delay, signal);
  }
  if (!signal?.aborted) onUpdate(text);
}
