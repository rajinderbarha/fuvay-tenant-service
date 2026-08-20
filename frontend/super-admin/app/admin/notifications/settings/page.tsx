import { redirect } from "next/navigation";

export default function NotificationSettingsRedirect() {
  redirect("/admin/notifications?tab=settings");
}
