import { redirect } from "next/navigation";

export default function NotificationTemplatesRedirect() {
  redirect("/admin/notifications?tab=templates");
}
