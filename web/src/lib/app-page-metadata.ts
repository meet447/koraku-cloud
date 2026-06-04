import type { Metadata } from "next";

export function appPageMetadata(title: string, description: string): Metadata {
  return {
    title: `${title} · Koraku`,
    description,
  };
}
