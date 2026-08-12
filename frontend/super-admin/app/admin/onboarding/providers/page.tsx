import { redirect } from "next/navigation";

/**
 * Backwards-compatible route for bookmarks and older navigation entries.
 * Home Services owns the only live provider-onboarding implementation, so
 * keep one canonical review workspace instead of two drifting admin pages.
 */
export default function LegacyProviderOnboardingPage() {
  redirect("/admin/home-services/providers?tab=onboarding");
}
