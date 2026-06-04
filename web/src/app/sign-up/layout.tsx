import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sign up · Koraku",
  description: "Create your Koraku account.",
};

export default function SignUpLayout({ children }: { children: React.ReactNode }) {
  return children;
}
