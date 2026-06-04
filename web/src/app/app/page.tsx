import type { Metadata } from "next";
import { appPageMetadata } from "@/lib/app-page-metadata";

export const metadata: Metadata = appPageMetadata(
  "Chat",
  "Chat with Koraku using your memory, tools, and connected apps.",
);

/** Chat UI is rendered by ``KorakuAppShell`` when the route is ``/app`` (see ``isAppChatRoute``). */
export default function AppHomePage() {
  return null;
}
