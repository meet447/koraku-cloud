import { redirect } from "next/navigation";
import { SETTINGS_PANEL_HREF } from "@/lib/settings-panel";

export default function SettingsIndexPage() {
  redirect(SETTINGS_PANEL_HREF.profile);
}
