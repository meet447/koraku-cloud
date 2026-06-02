import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

type SearchParams = Promise<{ next?: string }>;

export default async function SignUpPage({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const next = params.next?.trim();
  redirect(next ? `/sign-in?next=${encodeURIComponent(next)}` : "/sign-in");
}
