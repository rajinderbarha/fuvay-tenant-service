import { redirect } from "next/navigation";

/** Canonical entry point for tenant Home Services registration. */
export default function HomeServicesSetupEntryPage() {
  redirect("/tenant/home-services/setup/overview");
}
