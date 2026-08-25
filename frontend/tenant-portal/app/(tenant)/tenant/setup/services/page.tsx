import { redirect } from "next/navigation";

// Retired parallel wizard. The onboarding Services & Pricing page is the
// single write surface; the operational workspace links back to it for edits.
export default function LegacyTenantServiceSetupRedirect() {
  redirect(
    "/tenant/home-services/setup/services-pricing?return_to=%2Fhome-services%2Fservices",
  );
}
