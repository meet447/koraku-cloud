import { KorakuAppShell } from "@/components/KorakuAppShell";
import { bootstrapOrgCookie } from "@/lib/tenant/bootstrap-org";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  await bootstrapOrgCookie();
  return <KorakuAppShell>{children}</KorakuAppShell>;
}
