/** Legacy provider status entry point; lifecycle state now lives here. */
import { redirect } from "next/navigation";

export default function LegacyProviderStatusRedirect() {
  redirect("/onboarding-status");
}
