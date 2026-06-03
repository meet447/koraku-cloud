import type { Metadata } from "next";

export function legalMetadata(title: string, description: string): Metadata {
  return {
    title: `${title} — Koraku`,
    description,
  };
}
