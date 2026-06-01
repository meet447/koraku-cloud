import { redirect } from "next/navigation";
import { APP_BASE } from "@/lib/app-path";

/** Legacy route — memory UI moved to /app/memory */
export default function BrainRedirectPage() {
  redirect(`${APP_BASE}/memory`);
}
