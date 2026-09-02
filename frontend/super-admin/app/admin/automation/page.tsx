import { redirect } from "next/navigation";

/**
 * Automation currently has one authoring workspace. Keep the stable parent
 * route used by navigation and breadcrumbs while taking admins directly to
 * the actionable recommendation-rules screen.
 */
export default function AutomationPage() {
  redirect("/admin/automation/recommendation-rules");
}
