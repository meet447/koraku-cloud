import { redirect } from "next/navigation";
import { APP_BASE } from "@/lib/app-path";

export default function PersonalizationRedirectPage() {
  redirect(`${APP_BASE}/settings#personalization`);
}
