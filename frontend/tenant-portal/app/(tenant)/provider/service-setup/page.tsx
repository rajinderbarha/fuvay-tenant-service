import { redirect } from "next/navigation";

// Retired duplicate. Service setup and post-activation service management now
// share the canonical Services & Pricing workspace.
export default function LegacyProviderServiceSetupRedirect() {
  redirect("/home-services/services");
}
