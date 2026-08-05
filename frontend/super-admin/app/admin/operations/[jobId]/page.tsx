/**
 * FINAL-L5-05E — legacy Field Ops Job detail, superseded by the canonical
 * service_jobs-backed detail page. Legacy `jobs.id` values are not the same
 * identifier space as canonical `service_jobs.id` -- there is no guaranteed
 * 1:1 mapping, so this redirects to the canonical Bookings & Jobs workspace
 * (not a guessed canonical detail URL). The old `?legacy_id=` lookup param
 * is dropped rather than preserved -- the unified workspace has no
 * legacy-id search capability, so keeping the param would silently produce
 * a dead filter instead of an honest generic landing.
 */
import { redirect } from "next/navigation";

export default function LegacyOperationsJobRedirect() {
  redirect("/admin/home-services/bookings-jobs");
}
