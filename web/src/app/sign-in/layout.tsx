import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sign in · Koraku",
  description: "Sign in to Koraku with Google or GitHub.",
};

export default function SignInLayout({ children }: { children: React.ReactNode }) {
  return children;
}
