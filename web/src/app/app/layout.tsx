import { KorakuAppShell } from "@/components/KorakuAppShell";
import { OrgCookieBootstrap } from "@/components/OrgCookieBootstrap";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <OrgCookieBootstrap />
      <KorakuAppShell>{children}</KorakuAppShell>
    </>
  );
}
