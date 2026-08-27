import { redirect } from "next/navigation";

/** Compatibility route for the retired duplicate onboarding checklist. */
export default function RetiredOnboardingStatusPage() {
  redirect("/tenant/home-services/setup");
}
