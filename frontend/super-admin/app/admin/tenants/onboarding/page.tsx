/** Legacy tenant-onboarding URL retained for bookmarks and admin search. */
import { redirect } from "next/navigation";

export default function LegacyTenantOnboardingRedirect() {
  redirect("/admin/onboarding/providers");
}
